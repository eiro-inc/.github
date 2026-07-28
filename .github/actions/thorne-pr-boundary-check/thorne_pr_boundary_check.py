#!/usr/bin/env python3
"""Validate Thorne pull-request template boundary declarations.

Two lanes, chosen automatically from the files a PR changes:

* **device** — any changed file that is *not* carved out as non-device in the
  repo's ``.github/thorne-lanes.yml`` puts the PR on the device path, which
  requires the full boundary template (:func:`validate`). Everything is device
  by default; the lanes file lists only the non-device carve-outs.
* **non-device** — when *every* changed file is carved out as non-device, the
  PR takes the light path, which only requires a non-empty ``## Summary``
  (:func:`validate_light`) — except a non-device PR from a whitelisted actor
  (e.g. Dependabot).

Importable pure helpers: ``validate`` / ``validate_light`` (body -> error list),
``parse_non_device_globs``, ``glob_match``, ``device_paths``, ``is_whitelisted``.

As a script: reads ``PR_BODY`` plus ``REPO`` / ``PR_NUMBER`` / ``BASE_REF`` /
``GH_TOKEN``, determines the lane from the PR's changed files and the lanes
file on the base branch, writes a GitHub step summary, emits annotations, and
exits non-zero on failure. Fail-safe: if the lane cannot be determined, the
device (full) path is used.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

REQUIRED_SECTIONS = [
    "Summary",
    "Related Issue",
    "Thorne Scope",
    "DHF Trace",
    "Safety Class",
    "Verification",
    "Thorne Boundary Check",
    "Reviewer Notes",
]


def collapse_whitespace(text):
    """Collapse internal whitespace runs to a single space and trim.

    Template text copied between editors picks up double spaces, tabs, and
    non-breaking spaces. Collapsing every whitespace run to a single space lets
    a respaced heading or checklist item still match its canonical form, so the
    gate keys on wording rather than exact spacing. (Callers apply this per
    physical line, so a hard line wrap *inside* a single checklist item is not
    joined — that stays a mismatch, which fails closed.)
    """
    return re.sub(r"\s+", " ", text or "").strip()


# Every item constant below is normalized through collapse_whitespace at
# definition, and the PR-body side is normalized by checked_items/present_items.
# Both sides of every comparison are therefore canonical by construction, so no
# compare site re-normalizes and a future reflow of a long constant can't
# silently make the gate stop firing.
SCOPE_DEVICE_FUNCTION = collapse_whitespace("Device function")
SCOPE_NON_DEVICE_FUNCTION = collapse_whitespace("Non-device function")
SCOPE_MULTI_FUNCTION = collapse_whitespace("Multiple-Function impact assessment")
SCOPE_PRE_DESIGN = collapse_whitespace("Pre-design scaffolding under CMP §7")
SCOPE_DHF_ARTIFACT = collapse_whitespace("DHF/QMS artifact")
SCOPE_NOT_THORNE = collapse_whitespace("Not Thorne-related")

THORNE_SCOPE_ITEMS = frozenset({
    SCOPE_DEVICE_FUNCTION,
    SCOPE_NON_DEVICE_FUNCTION,
    SCOPE_MULTI_FUNCTION,
    SCOPE_PRE_DESIGN,
    SCOPE_DHF_ARTIFACT,
    SCOPE_NOT_THORNE,
})

SAFETY_NA = collapse_whitespace("N/A")
SAFETY_TBD = collapse_whitespace("TBD / blocked until resolved")
SAFETY_C_ADJACENT = collapse_whitespace("C-adjacent integrity control")
SAFETY_CONCRETE_CLASSES = frozenset(map(collapse_whitespace, (
    "Class A",
    "Class B",
    "Class C",
)))
SAFETY_CLASS_ITEMS = frozenset(map(collapse_whitespace, (
    "Class A",
    "Class B",
    "Class C",
    "N/A",
    "TBD / blocked until resolved",
)))

# Boundary confirmations every Thorne-related PR must make. Tuples (order is the
# error-message order); each element is normalized at definition.
MANDATORY_BOUNDARY_ITEMS = tuple(map(collapse_whitespace, (
    "This PR does not introduce Eiro-authored clinical interpretation.",
    "This PR does not introduce safety detection, safety flagging, triage, crisis prediction, priority ranking, patient-status assignment, or treatment recommendation.",
    "This PR does not introduce PHQ-9 item 9 default alerting, urgent notification, 24-hour, push, or on-call alert behavior.",
    "This PR does not change the meaning, priority, salience, or safety significance of device output from a non-device surface.",
)))

# Boundary confirmations required only for the scope that triggers them.
PRE_DESIGN_BOUNDARY_ITEMS = tuple(map(collapse_whitespace, (
    "If this is pre-design scaffolding, it stays within CMP §7 and does not implement clinical device behavior.",
)))

# Full set the template renders (used for checklist-completeness validation).
ALL_BOUNDARY_ITEMS = MANDATORY_BOUNDARY_ITEMS + PRE_DESIGN_BOUNDARY_ITEMS

# Scopes for which a substantive DHF Trace is mandatory.
DHF_TRACE_REQUIRED_SCOPES = frozenset({
    SCOPE_DEVICE_FUNCTION,
    SCOPE_MULTI_FUNCTION,
    SCOPE_PRE_DESIGN,
    SCOPE_DHF_ARTIFACT,
})

# Source changes that implement a device function or affect a device item
# through a Multiple-Function use must identify the concrete architecture item
# and its class. The dedicated template section is preferred; the DHF Trace is
# also scanned so PRs opened from the immediately preceding template do not
# fail solely because they lack the new heading.
AFFECTED_ITEM_REQUIRED_SCOPES = frozenset({
    SCOPE_DEVICE_FUNCTION,
    SCOPE_MULTI_FUNCTION,
})
AFFECTED_ITEM_SECTION = "Affected Device Software Items"
AFFECTED_ITEM_CLASS_RE = re.compile(
    r"(?i)\b(ARC-\d{2})\b[^\n]{0,120}?\b(Class\s+[ABC])\b"
)

# A DHF Trace is substantive when it cites at least one recognizable DHF/QMS
# anchor. The vocabulary covers the DHF document-ID families named in the PR
# template (DDS, DDP, UNS, SRS, SDD, IFS, HAZ, DR, VVP, VVR, RMP, RMF, CMP,
# TRM, ADR) and the cross-repo eiro-qms families (SOP, FRM, POL, REC), plus
# section references and external standard citations. Testing for anchor
# *presence* (rather than matching a placeholder phrase) does not break when
# the template's hint text changes, and rejects freeform non-anchor text.
ANCHOR_RE = re.compile(
    r"(?i)"
    r"\b(?:ADR|SOP|FRM|POL|REC|UNS|SRS|SDD|IFS|HAZ|DR|VVP|VVR|DDP)-\d{1,4}(?:-\d{1,3})?\b"
    r"|\b(?:DDS|DDP|RMP|RMF|CMP|TRM)\b"
    r"|§\s*\d"
    r"|\b21\s*CFR\b|\bISO\s*\d|\bIEC\s*\d"
)


def normalize_heading(text):
    return collapse_whitespace(text).lower()


def sections(markdown):
    """Map normalized ``## heading`` -> section body text."""
    found = {}
    # ATX headings only at column 0, with a literal space or tab after ``##``.
    # Deliberately stricter than CommonMark's 0-3 leading spaces: an indented
    # ``##`` line is list-continuation text, not a heading, and honoring it would
    # let an example heading inside Reviewer Notes overwrite (last-wins) the real
    # section and pass a PR that confirmed nothing. ``[ \t]`` (not ``\s``) so a
    # bare ``##`` before a newline, or ``##`` + non-breaking space — which GitHub
    # renders as plain text, not a heading — cannot forge a required section.
    # Known gap (pre-existing): ``## X`` inside a fenced code block still parses.
    matches = list(re.finditer(r"(?m)^##[ \t]+(.+?)[ \t]*$", markdown))
    for index, match in enumerate(matches):
        title = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        found[normalize_heading(title)] = markdown[start:end].strip()
    return found


def checked_items(section_text):
    checked = set()
    for line in section_text.splitlines():
        match = re.match(r"^\s*-\s+\[[xX]\]\s+(.+?)\s*$", line)
        if match:
            checked.add(collapse_whitespace(match.group(1)))
    return checked


def present_items(section_text):
    present = set()
    for line in section_text.splitlines():
        match = re.match(r"^\s*-\s+\[[ xX]\]\s+(.+?)\s*$", line)
        if match:
            present.add(collapse_whitespace(match.group(1)))
    return present


def substantive_text(section_text):
    """Section text with HTML comments and checkbox lines removed.

    Comments are stripped across the whole section first (DOTALL) so a
    multi-line template comment does not leak its inner lines as substantive
    text; the per-line pass then drops blanks and checkbox lines.
    """
    without_comments = re.sub(r"<!--.*?-->", "", section_text, flags=re.DOTALL)
    cleaned = []
    for line in without_comments.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- ["):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


NEW_DEPENDENCIES_SECTION = "New Dependencies"

# Files whose change means the PR touches the dependency set (CMP §10).
# Covers the ecosystems of the current device repos (npm, Cargo, Gradle,
# SwiftPM) plus Python and Go so a future runtime dependency in those
# ecosystems does not sail through unmatched. A new ecosystem's manifest
# names are added here deliberately, with a matching test.
_DEPENDENCY_MANIFEST_NAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Cargo.toml",
    "Cargo.lock",
    "gradle.lockfile",
    "libs.versions.toml",
    "Package.swift",
    "Package.resolved",
    "pyproject.toml",
    "poetry.lock",
    "uv.lock",
    "go.mod",
    "go.sum",
}
_DEPENDENCY_MANIFEST_SUFFIXES = (".gradle", ".gradle.kts")
_DEPENDENCY_MANIFEST_RES = (re.compile(r"^requirements[^/]*\.txt$"),)


def dependency_manifest_paths(changed_files):
    """Changed files that are dependency manifests or lockfiles."""
    hits = []
    for path in changed_files:
        base = path.rsplit("/", 1)[-1]
        if (
            base in _DEPENDENCY_MANIFEST_NAMES
            or base.endswith(_DEPENDENCY_MANIFEST_SUFFIXES)
            or any(pattern.match(base) for pattern in _DEPENDENCY_MANIFEST_RES)
        ):
            hits.append(path)
    return hits


DEPENDENCY_CHECK_UNAVAILABLE = (
    "The PR's changed files could not be determined, so the CMP §10 New "
    "Dependencies check could not run. Re-run the check; if the failure "
    "persists, verify the '## New Dependencies' declaration manually."
)


def validate_new_dependencies(body, manifest_hits):
    """CMP §10: a manifest change requires a substantive New Dependencies declaration.

    ``manifest_hits`` is the manifest/lockfile subset of the PR's *device-lane
    triggering paths* (files not carved out as non-device). CMP §10's
    identification duty follows the CMP's device-configuration scope (CMP §2,
    §4.1): a manifest wholly under a non-device carve-out is outside the device
    configuration and does not demand a declaration, and a carved-out manifest
    riding along in a device-lane PR does not trigger one either.

    ``manifest_hits is None`` means the changed files are *unknown* (lane
    fail-safe paths) — the check reports that it could not run rather than
    passing silently.

    A bare "None" is rejected when manifests changed — say *why* the change
    introduces no new/upgraded dependency (e.g. "None — lockfile refresh only").
    """
    if manifest_hits is None:
        return [DEPENDENCY_CHECK_UNAVAILABLE]
    if not manifest_hits:
        return []
    parsed = sections(body or "")
    text = substantive_text(parsed.get(normalize_heading(NEW_DEPENDENCIES_SECTION), ""))
    bare = text.lower().strip("-*_ .!\t")
    if text and bare != "none":
        return []
    shown = ", ".join(f"`{path}`" for path in manifest_hits[:5])
    if len(manifest_hits) > 5:
        shown += f", and {len(manifest_hits) - 5} more"
    return [
        "Dependency manifests changed (" + shown + ") but '## New Dependencies' "
        "has no substantive declaration. List each new or upgraded dependency "
        "(name@version — runtime|dev — device path? — purpose — license — "
        "maintenance note — known CVEs/advisories checked), or state why none "
        "is introduced (e.g. 'None — lockfile refresh only, no dependency "
        "changes'). Per CMP §10."
    ]


def validate(body):
    """Return a list of declaration errors for the given PR body."""
    body = body or ""
    if not body.strip():
        # Short-circuit: one actionable error instead of one-per-section noise.
        return ["PR body is empty. Use the organization Thorne PR template."]
    parsed = sections(body)
    errors = []

    for section in REQUIRED_SECTIONS:
        if normalize_heading(section) not in parsed:
            errors.append(f"Missing required section: ## {section}")

    checkbox_expected = {
        "Thorne Scope": THORNE_SCOPE_ITEMS,
        "Safety Class": SAFETY_CLASS_ITEMS,
        "Thorne Boundary Check": frozenset(ALL_BOUNDARY_ITEMS),
    }
    for section, expected in checkbox_expected.items():
        text = parsed.get(normalize_heading(section), "")
        if not text:
            continue
        missing = sorted(expected - present_items(text))
        if missing:
            errors.append(
                f"Section ## {section} is missing checklist item(s): {', '.join(missing)}"
            )

    scope_checked = checked_items(parsed.get(normalize_heading("Thorne Scope"), ""))
    safety_checked = checked_items(parsed.get(normalize_heading("Safety Class"), ""))
    boundary_checked = checked_items(parsed.get(normalize_heading("Thorne Boundary Check"), ""))

    thorne_scopes = scope_checked - {SCOPE_NOT_THORNE}
    not_thorne = SCOPE_NOT_THORNE in scope_checked
    if not scope_checked:
        errors.append("Select at least one Thorne Scope item.")
    if not_thorne and thorne_scopes:
        errors.append("Do not combine 'Not Thorne-related' with Thorne-specific scope items.")

    if thorne_scopes:
        if scope_checked & DHF_TRACE_REQUIRED_SCOPES:
            trace = substantive_text(parsed.get(normalize_heading("DHF Trace"), ""))
            if not ANCHOR_RE.search(trace):
                errors.append(
                    "Add DHF Trace text citing at least one controlling anchor "
                    "(e.g., DDS §5, ADR-0002, SRS-02-04, CMP §7) for this Thorne-scoped PR."
                )

        if scope_checked & AFFECTED_ITEM_REQUIRED_SCOPES:
            concrete_safety = safety_checked & SAFETY_CONCRETE_CLASSES
            if not concrete_safety:
                errors.append(
                    "Device-function and Multiple-Function-impact PRs must select "
                    "at least one concrete Safety Class (Class A, B, or C)."
                )

            affected_text = "\n".join((
                substantive_text(
                    parsed.get(normalize_heading(AFFECTED_ITEM_SECTION), "")
                ),
                substantive_text(parsed.get(normalize_heading("DHF Trace"), "")),
            ))
            affected_mappings = AFFECTED_ITEM_CLASS_RE.findall(affected_text)
            if not affected_mappings:
                errors.append(
                    "Identify at least one affected device software item and class "
                    "as 'ARC-NN — Class A/B/C' under ## Affected Device Software "
                    "Items (or in the DHF Trace for a pre-template PR). Product "
                    "scope and item class are separate: a non-device function with "
                    "Multiple-Function impact may identify ARC-04 — Class C."
                )
            else:
                mapped_classes = {
                    collapse_whitespace(f"Class {class_name[-1].upper()}")
                    for _, class_name in affected_mappings
                }
                unchecked_classes = mapped_classes - concrete_safety
                if unchecked_classes:
                    errors.append(
                        "Select every Safety Class named by an affected ARC item: "
                        + ", ".join(sorted(unchecked_classes))
                    )
                unmapped_classes = concrete_safety - mapped_classes
                if unmapped_classes:
                    errors.append(
                        "Every selected Safety Class must map to an affected ARC "
                        "item: " + ", ".join(sorted(unmapped_classes))
                    )

            if SAFETY_NA in safety_checked and concrete_safety:
                errors.append("Do not combine Safety Class N/A with Class A, B, or C.")
            if SAFETY_TBD in safety_checked:
                errors.append(
                    "Resolve 'TBD / blocked until resolved' before merge and select "
                    "the affected software item's concrete class."
                )

        if SAFETY_C_ADJACENT in safety_checked:
            errors.append(
                "'C-adjacent integrity control' is not a software safety class; "
                "identify each affected ARC item and select Class A, B, or C."
            )

        for item in MANDATORY_BOUNDARY_ITEMS:
            if item not in boundary_checked:
                errors.append(f"Thorne-related PRs must confirm boundary item: {item}")

        if SCOPE_PRE_DESIGN in scope_checked:
            for item in PRE_DESIGN_BOUNDARY_ITEMS:
                if item not in boundary_checked:
                    errors.append(f"Pre-design scaffolding PRs must confirm boundary item: {item}")

    return errors


# PR actors whose non-device PRs are whitelisted (no authored body required) —
# trusted automation. Matched against github.actor, so a human editing the PR
# de-whitelists it and is then asked for a Summary.
WHITELISTED_ACTORS = {"dependabot[bot]"}


def is_whitelisted(actor):
    return (actor or "").strip() in WHITELISTED_ACTORS


def validate_light(body, actor=""):
    """Non-device (light) lane: require only a non-empty ``## Summary`` or whitelisted actor."""
    if is_whitelisted(actor):
        return []
    parsed = sections(body or "")
    if not substantive_text(parsed.get(normalize_heading("Summary"), "")):
        return [
            "Light-lane PR (non-device paths only): add a non-empty ## Summary "
            "describing the change."
        ]
    return []


# -----------------------------------------------------------------------------
# Lane determination (device by default; non-device paths are carved out)

LANES_PATH = ".github/thorne-lanes.yml"
GITHUB_API = "https://api.github.com"


def parse_non_device_globs(yaml_text):
    """Extract the ``non_device:`` list from a (minimal) thorne-lanes.yml.

    Understands the documented block shape only::

        non_device:
          - "glob"
          - glob

    Comments and blank lines are ignored. Returns ``[]`` when the key is
    absent or empty — i.e., the whole repo is device by default.
    """
    globs = []
    in_list = False
    for raw in (yaml_text or "").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if re.match(r"^non_device\s*:\s*\[\s*\]\s*$", line):
            # Explicit empty list: declares no carve-outs. Must NOT open block
            # mode, or a (malformed) trailing "- glob" would be read as a
            # carve-out — the opposite of what `[]` declares — and weaken the gate.
            continue
        if re.match(r"^non_device\s*:\s*$", line):
            in_list = True
            continue
        if in_list:
            match = re.match(r"^\s*-\s*(.+?)\s*$", line)
            if match:
                value = match.group(1).strip().strip('"').strip("'")
                if value:
                    globs.append(value)
            elif not line[:1].isspace():
                in_list = False  # a new top-level key ends the list
    return globs


def _glob_to_regex(glob):
    """Translate a path glob to a regex.

    ``**`` matches across directory separators (any depth); ``*`` matches
    within a single path segment; ``?`` matches one non-separator character.
    """
    i, n = 0, len(glob)
    out = ["^"]
    while i < n:
        char = glob[i]
        if char == "*":
            if glob[i : i + 2] == "**":
                i += 2
                if i < n and glob[i] == "/":
                    i += 1
                out.append(".*")
            else:
                out.append("[^/]*")
                i += 1
        elif char == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(char))
            i += 1
    out.append("$")
    return "".join(out)


def glob_match(path, glob):
    """True if ``path`` matches the gitignore-style ``glob``.

    A glob with no wildcard is treated as a path prefix: ``src/ui`` matches
    ``src/ui`` and anything beneath it.
    """
    candidate = (glob or "").strip()
    if not candidate:
        return False
    if not any(ch in candidate for ch in "*?"):
        candidate = candidate.rstrip("/")
        return path == candidate or path.startswith(candidate + "/")
    return re.match(_glob_to_regex(candidate), path) is not None


def device_paths(changed_files, non_device_globs):
    """Changed files that are NOT carved out as non-device (device by default).

    The PR is on the device lane when this list is non-empty.
    """
    return [
        path
        for path in changed_files
        if not any(glob_match(path, glob) for glob in non_device_globs)
    ]


def _gh_get(path):
    token = os.environ.get("GH_TOKEN", "")
    req = urllib.request.Request(GITHUB_API + path)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_changed_files(repo, pr_number):
    """Return the changed file paths in the PR (paginated).

    A renamed file is reported by the API as a single entry whose ``filename``
    is the *new* path and whose ``previous_filename`` is the old path. Both are
    returned, so moving a device file into a non-device carve-out still surfaces
    the device path and keeps the PR on the device lane.
    """
    files = []
    page = 1
    while True:
        batch = _gh_get(f"/repos/{repo}/pulls/{pr_number}/files?per_page=100&page={page}")
        if not batch:
            break
        for item in batch:
            files.append(item["filename"])
            previous = item.get("previous_filename")
            if previous:
                files.append(previous)
        if len(batch) < 100:
            break
        page += 1
    return files


def fetch_non_device_globs(repo, ref):
    """Read non_device globs from thorne-lanes.yml at ``ref`` on ``repo``.

    Reads from the PR base ref (not head) so a PR cannot weaken its own lane by
    editing the lanes file in the same PR. A missing file means no carve-outs.
    """
    try:
        data = _gh_get(f"/repos/{repo}/contents/{LANES_PATH}?ref={ref}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        raise
    content = base64.b64decode(data.get("content", "")).decode("utf-8")
    return parse_non_device_globs(content)


def determine_lane():
    """Return ``(lane, triggering_paths, note)``.

    ``lane`` is ``"device"`` or ``"non_device"``. ``triggering_paths`` lists the
    changed files that forced the device lane (for an actionable message, and
    as the input to the CMP §10 dependency check). ``triggering_paths is None``
    means the changed files could not be determined (fail-safe paths): the lane
    falls back to ``"device"``, and downstream consumers must treat the file
    list as *unknown*, not empty. Fail-safe: any inability to determine the
    lane yields ``"device"``.
    """
    repo = os.environ.get("REPO", "").strip()
    pr_number = os.environ.get("PR_NUMBER", "").strip()
    base_ref = os.environ.get("BASE_REF", "").strip()

    if not (repo and pr_number):
        return "device", None, "PR context unavailable; defaulting to the device (full) path."
    try:
        changed = fetch_changed_files(repo, pr_number)
        globs = fetch_non_device_globs(repo, base_ref) if base_ref else []
    except Exception as exc:  # noqa: BLE001 — any API failure must fail safe to device
        return "device", None, f"Could not determine lane from changed paths ({exc}); defaulting to the device (full) path."

    if not changed:
        return "device", None, "No changed files reported; defaulting to the device (full) path."
    triggering = device_paths(changed, globs)
    if triggering:
        return "device", triggering, ""
    actor = os.environ.get("PR_ACTOR", "").strip()
    note = f"Whitelisted actor ({actor}); auto-approved." if is_whitelisted(actor) else ""
    return "non_device", [], note


def main():
    body = os.environ.get("PR_BODY")
    actor = os.environ.get("PR_ACTOR", "")
    lane, triggering, note = determine_lane()
    errors = validate(body) if lane == "device" else validate_light(body, actor)

    dep_mode = os.environ.get("DEPENDENCY_CHECK_MODE", "warn").strip().lower()
    if dep_mode not in {"warn", "fail"}:
        errors.append(
            f"Invalid dependency-check-mode '{dep_mode}'; use 'warn' or 'fail'."
        )
        dep_mode = "fail"  # a misconfigured gate must be loud, not silently lax
    dep_warnings = []
    if lane == "device":
        manifest_hits = dependency_manifest_paths(triggering) if triggering is not None else None
        dep_messages = validate_new_dependencies(body, manifest_hits)
        if dep_mode == "fail":
            errors.extend(dep_messages)
        else:
            dep_warnings = dep_messages

    lane_label = "device (full template)" if lane == "device" else "non-device (light)"
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("## Thorne PR Boundary Check\n\n")
            handle.write(f"**Lane:** {lane_label}\n\n")
            if note:
                handle.write(f"_{note}_\n\n")
            if lane == "device" and triggering:
                handle.write(
                    "On the device path because these changed files are not carved out as "
                    "non-device in `.github/thorne-lanes.yml`:\n\n"
                )
                for path in triggering[:20]:
                    handle.write(f"- `{path}`\n")
                if len(triggering) > 20:
                    handle.write(f"- …and {len(triggering) - 20} more\n")
                handle.write("\n")
            for warning in dep_warnings:
                handle.write(f"⚠️ {warning}\n\n")
            if errors:
                handle.write("Failed checks:\n\n")
                for error in errors:
                    handle.write(f"- {error}\n")
            else:
                handle.write("All required PR boundary declarations are present.\n")

    if note:
        print(f"::notice::{note}")
    if lane == "device" and triggering:
        shown = ", ".join(triggering[:10])
        if len(triggering) > 10:
            shown += f", and {len(triggering) - 10} more"
        print(f"::notice::Device path triggered by: {shown}")

    for warning in dep_warnings:
        print(f"::warning::{warning}")

    if errors:
        for error in errors:
            print(f"::error::{error}")
        sys.exit(1)

    print(f"Thorne PR boundary declarations are complete (lane: {lane}).")


if __name__ == "__main__":
    main()
