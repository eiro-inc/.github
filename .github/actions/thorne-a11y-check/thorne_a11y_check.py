#!/usr/bin/env python3
"""Validate the Thorne pull-request ``## Accessibility`` declaration.

Accessibility cuts the **UI / non-UI axis** — a *different* axis from the
device / non-device lanes enforced by ``thorne-pr-boundary-check``. The two
gates are siblings: neither subsumes the other, and a single PR may be both
device (full boundary block) and UI (accessibility block).

Two lanes, chosen automatically from the files a PR changes:

* **ui** — a changed file that is part of the UI surface puts the PR on the UI
  path, which requires the template's ``## Accessibility`` section to be filled
  (:func:`validate_accessibility`). The UI surface is resolved as the
  ``review-a11y`` skill resolves it (SKILL.md § "UI-surface determination"):

  1. the repo's ``.github/thorne-lanes.yml`` ``ui:`` glob block is authoritative
     when present (an *allowlist* — nothing is UI by default, the inverse of the
     ``non_device:`` carve-out list the boundary check reads from the same file);
  2. when there is **no** ``ui:`` block yet (Phase-1 repos), a file-path
     heuristic mirrors the skill's fallback (``*.svelte``, ``**/ui/**``,
     ``res/values/**`` …). The Action can only see paths, so the skill's
     content-based signals (``@Composable`` functions, SwiftUI ``View`` types,
     "components that render markup") are approximated by path and documented as
     a known gap.
* **non-ui** — when no changed file is part of the UI surface, the PR takes the
  light path and the accessibility section is not required.

The lane decision is always written to the step summary, and any ambiguity in
the lanes file (a mis-cased key, an unparseable ``ui:`` shape) is surfaced as an
annotation — the gate is *loud* about finding no UI surface, so a mis-keyed
lanes file cannot leave a permanently green required check unnoticed.

Importable pure helpers: ``validate_accessibility`` (body -> error list),
``parse_ui_globs``, ``glob_match``, ``ui_paths``, ``required_item_ids``,
``checkbox_lines``, ``lead_kind``, ``sole_item_id``.

As a script: reads ``PR_BODY`` plus ``REPO`` / ``PR_NUMBER`` / ``BASE_REF`` /
``GH_TOKEN``, determines the surface from the PR's changed files and the lanes
file on the base branch, writes a GitHub step summary, emits annotations, and
exits non-zero on failure. Fail-safe: if the UI surface cannot be determined,
the accessibility section is required *in full* (the stricter path) — including
the web-only item, since "web?" is unknown.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

ACCESSIBILITY_SECTION = "Accessibility"

# Human-judgment checks whose home is the template's ## Accessibility section
# (thorne-product#55). Matched by their stable IDs — not full text — so a reword
# of an item's wording in the template does not silently disarm the gate, per
# the accessibility design's "reference checks by their stable IDs". Keep this
# tuple in sync with the template's human items (design/accessibility.md, the
# PR-template checklist table).
HUMAN_ITEM_IDS = (
    "SR-01",
    "SR-02",
    "CD-03",
    "FORM-01",
    "TYPE-02",
    "TYPE-03",
    "COLOR-03",
    "FOCUS-01",
)

# Items whose applicability is scoped to a stack. TYPE-03 (content reflow) is
# web-only (design/accessibility.md: Surfaces = web), so it is required *ticked*
# only when the PR's UI surface includes a web path. It must still be *present*
# in the template on every UI PR (the template renders all items); a native PR
# simply leaves it unticked rather than asserting an untrue web claim.
WEB_ONLY_ITEM_IDS = frozenset({"TYPE-03"})

# A checkbox item's stable ID, e.g. "SR-01" / "FORM-01" / "COLOR-03".
_ITEM_ID_RE = re.compile(r"\b([A-Z]{2,6}-\d{2})\b")

# Emphasis / code markers stripped before a lead line is classified.
_EMPHASIS_RE = re.compile(r"[*_`]+")

# A GFM task-list line, accepting the three list bullets GFM renders (-, *, +).
_CHECKBOX_RE = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s+(.+?)\s*$")


def collapse_whitespace(text):
    """Collapse internal whitespace runs to a single space and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_heading(text):
    return collapse_whitespace(text).lower()


# -----------------------------------------------------------------------------
# Section extraction (fenced-code aware, bounded, duplicate-detecting)

_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
_ATX_H2_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*$")
_DETAILS_CLOSE_RE = re.compile(r"(?i)^</details>\s*$")


def section_bodies(markdown, heading):
    """Return every body under a ``## <heading>`` matching ``heading``.

    A section body runs from just after its heading to the first of: the next
    column-0 ``##`` heading, a column-0 ``</details>``, or end of body. Bounding
    at ``</details>`` matters because the template renders ``## Accessibility``
    as the final heading *inside* a ``<details>`` wrapper — without the bound the
    "section" would swallow the closing tag and anything appended after it (e.g.
    pasted review feedback that quotes a blank checklist), producing spurious
    passes and failures.

    Headings and closers inside fenced code blocks or indented (>= 4-space) code
    are ignored, so forged or quoted markup cannot open or extend a section.

    Returns a list so a caller can detect a duplicate heading (two ``##
    Accessibility`` sections are ambiguous) rather than silently taking the last.
    """
    lines = (markdown or "").split("\n")
    in_fence = False
    fence_char = None
    headings = []  # (line_index, normalized_title)
    boundaries = []  # line indices that terminate a section
    for idx, line in enumerate(lines):
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        fence = _FENCE_RE.match(stripped)
        if fence and indent < 4:
            marker = fence.group(1)[0]
            if not in_fence:
                in_fence, fence_char = True, marker
            elif marker == fence_char:
                in_fence, fence_char = False, None
            continue
        if in_fence or indent >= 4:
            continue
        atx = _ATX_H2_RE.match(line)
        if atx:
            headings.append((idx, normalize_heading(atx.group(1))))
            boundaries.append(idx)
        elif _DETAILS_CLOSE_RE.match(line):
            boundaries.append(idx)
    boundaries.sort()
    target = normalize_heading(heading)
    bodies = []
    for h_idx, title in headings:
        if title != target:
            continue
        end = len(lines)
        for boundary in boundaries:
            if boundary > h_idx:
                end = boundary
                break
        bodies.append("\n".join(lines[h_idx + 1 : end]).strip())
    return bodies


def _strip_comments(text):
    """Drop HTML comments so commented-out checkboxes/prose never count."""
    return re.sub(r"<!--.*?-->", "", text or "", flags=re.DOTALL)


def checkbox_lines(section_text):
    """Return ``(ticked, text)`` for each task-list line, in document order.

    ``text`` is whitespace-collapsed. Both ``[x]`` and ``[X]`` count as ticked.
    """
    out = []
    for line in section_text.splitlines():
        match = _CHECKBOX_RE.match(line)
        if match:
            out.append((match.group(1).lower() == "x", collapse_whitespace(match.group(2))))
    return out


def _plain(text):
    """Lowercased text with emphasis/code markers removed (for lead matching)."""
    return collapse_whitespace(_EMPHASIS_RE.sub("", text or "")).lower()


def lead_kind(text):
    """Classify a checkbox line as a lead box: ``'changes'`` | ``'na'`` | ``None``.

    A line carrying *any* stable item ID is an item line, never a lead — so a
    web-annotated ``**TYPE-03** *(web)* — N/A …`` item cannot be misread as the
    N/A lead. The lead phrases are anchored at the *start* of the line (after
    stripping emphasis), so an ordinary sentence that merely contains the words
    "no user-facing UI change" further down cannot stand in for a lead box.
    """
    if _ITEM_ID_RE.search(text):
        return None
    plain = _plain(text)
    if plain.startswith("n/a") or plain == "na" or plain.startswith("na "):
        return "na"
    if plain.startswith("this pr changes user-facing ui") or plain.startswith(
        "changes user-facing ui"
    ):
        return "changes"
    return None


def sole_item_id(text):
    """The stable ID of a checkbox line, iff it carries exactly one.

    Requiring a *sole* ID means one line listing several IDs
    (``- [x] Reviewed SR-01, SR-02, … with the skill``) confirms none of them:
    each of the eight items must be its own distinct ticked line.
    """
    ids = set(_ITEM_ID_RE.findall(text))
    return next(iter(ids)) if len(ids) == 1 else None


def required_item_ids(is_web):
    """Item IDs whose tick is required for the PR's surface.

    ``TYPE-03`` (web content reflow) is required only when a web surface is in
    scope; on a native-only PR it is optional (present but may stay unticked).
    """
    if is_web:
        return HUMAN_ITEM_IDS
    return tuple(i for i in HUMAN_ITEM_IDS if i not in WEB_ONLY_ITEM_IDS)


def validate_accessibility(body, required_ids=HUMAN_ITEM_IDS):
    """Return a list of declaration errors for the ``## Accessibility`` section.

    Called only on the UI lane. Requires:

    * exactly one ``## Accessibility`` section (a duplicate heading is ambiguous);
    * both lead checkboxes present, with exactly one ticked (XOR);
    * ``N/A`` ticked -> pass (a touched UI file may still be a non-user-facing
      change; the reviewer owns that call, mirroring how the boundary gate
      trusts the declared scope);
    * ``changes user-facing UI`` ticked -> every human item *present* (template
      integrity) and every item in ``required_ids`` ticked. ``required_ids``
      lets the caller drop the web-only item on a native-only surface.
    """
    body = body or ""
    if not body.strip():
        return [
            "PR body is empty. This PR changes user-facing UI — fill the "
            "## Accessibility section of the Thorne PR template (WCAG 2.2 AA)."
        ]

    bodies = section_bodies(body, ACCESSIBILITY_SECTION)
    if not bodies:
        return [
            "Missing required section: ## Accessibility. This PR changes "
            "user-facing UI; fill the accessibility checklist (WCAG 2.2 AA)."
        ]
    if len(bodies) > 1:
        return [
            "Found more than one '## Accessibility' section in the PR body. Keep "
            "exactly one — a duplicate heading (for example pasted review "
            "feedback that quotes the checklist) makes the declaration ambiguous."
        ]

    lines = checkbox_lines(_strip_comments(bodies[0]))
    errors = []

    # Lead boxes, matched per-line so an item line or an incidental bullet
    # cannot stand in for a lead.
    changes_present = changes_ticked = na_present = na_ticked = False
    for ticked, text in lines:
        kind = lead_kind(text)
        if kind == "changes":
            changes_present = True
            changes_ticked = changes_ticked or ticked
        elif kind == "na":
            na_present = True
            na_ticked = na_ticked or ticked

    if not changes_present:
        errors.append(
            "## Accessibility is missing the lead checkbox "
            "'This PR changes user-facing UI'."
        )
    if not na_present:
        errors.append(
            "## Accessibility is missing the lead checkbox "
            "'N/A — no user-facing UI change'."
        )

    if not (changes_ticked or na_ticked):
        errors.append(
            "Tick exactly one Accessibility lead box: 'This PR changes "
            "user-facing UI' or 'N/A — no user-facing UI change'."
        )
    if changes_ticked and na_ticked:
        errors.append(
            "Do not tick both Accessibility lead boxes; choose 'changes "
            "user-facing UI' or 'N/A'."
        )

    if changes_ticked and not na_ticked:
        # Per-line ID -> ticked map: each item must be the ID of a distinct line.
        ticked_by_id = {}
        for ticked, text in lines:
            item_id = sole_item_id(text)
            if item_id:
                ticked_by_id[item_id] = ticked_by_id.get(item_id, False) or ticked

        missing = [i for i in HUMAN_ITEM_IDS if i not in ticked_by_id]
        if missing:
            errors.append(
                "## Accessibility is missing checklist item(s): "
                + ", ".join(missing)
                + "."
            )
        unconfirmed = [
            i for i in required_ids if i in ticked_by_id and not ticked_by_id[i]
        ]
        if unconfirmed:
            errors.append(
                "Confirm each Accessibility item for the surfaces this PR "
                "touches — unticked: " + ", ".join(unconfirmed) + " (WCAG 2.2 AA)."
            )

    return errors


# -----------------------------------------------------------------------------
# UI-surface determination (non-UI by default; ui: globs opt files IN)

LANES_PATH = ".github/thorne-lanes.yml"
GITHUB_API = "https://api.github.com"

# Phase-1 fallback heuristic (review-a11y SKILL.md § "UI-surface determination",
# step 2). Used only when a repo has no ``ui:`` block yet. Path-based
# approximation of the skill's per-stack signals; content-based signals it also
# names (@Composable, SwiftUI View types, JS/TS components that render markup)
# cannot be seen from paths alone and are a documented gap.
HEURISTIC_WEB_GLOBS = (
    "**/*.svelte",
    "**/*.css",
    "**/*.scss",
    "**/src/routes/**",
    "**/src/lib/**",
)
HEURISTIC_NATIVE_GLOBS = (
    "**/ui/**",
    "**/res/layout/**",
    "**/res/values/**",
    "**/res/drawable*/**",
    "**/res/mipmap*/**",
    "**/res/font/**",
    "**/*.xib",
    "**/*.storyboard",
    "**/*.xcassets/**",
)
HEURISTIC_UI_GLOBS = HEURISTIC_WEB_GLOBS + HEURISTIC_NATIVE_GLOBS


class LanesError(ValueError):
    """A ``ui:`` declaration in thorne-lanes.yml whose shape the parser can't honor."""


def parse_ui_globs(yaml_text):
    """Extract the ``ui:`` list from a (minimal) thorne-lanes.yml.

    Returns ``(globs, saw_ui_key, warnings)``:

    * ``globs`` — the declared UI globs (``[]`` for ``ui: []`` or no key);
    * ``saw_ui_key`` — whether a lowercase ``ui:`` key was present. This
      distinguishes an *authoritative* empty declaration (``ui: []`` — the repo
      says it has no UI surface) from *no declaration yet* (Phase-1 repo — fall
      back to the heuristic), which the two callers treat differently;
    * ``warnings`` — human-readable notes worth surfacing (e.g. a mis-cased key).

    Understands the documented block shape only::

        ui:
          - "glob"
          - glob

    Raises :class:`LanesError` on an inline shape the parser cannot honor
    (``ui: ["glob"]`` flow style, ``ui: "glob"`` scalar) rather than silently
    reading no UI surface — a parse miss must fail *loud/strict*, not fail open,
    which is the inverse of what silently returning ``[]`` would do.
    """
    globs = []
    warnings = []
    saw_key = False
    in_list = False
    for raw in (yaml_text or "").splitlines():
        # Strip a YAML end-of-line comment: '#' at line start, or preceded by
        # whitespace. A '#' with no leading space (e.g. inside a glob like
        # "src/c#/**") is NOT a comment and is left intact.
        line = re.sub(r"(^|\s)#.*$", r"\1", raw).rstrip()
        if not line.strip():
            continue

        key = re.match(r"^ui\s*:\s*(.*)$", line)
        if key:
            saw_key = True
            rest = key.group(1).strip()
            if rest == "":
                in_list = True
            elif rest == "[]":
                in_list = False  # explicit empty: authoritative "no UI surface"
            else:
                raise LanesError(
                    f"unsupported inline `ui:` value {rest!r}; declare a block "
                    'list (`ui:` then indented `- "glob"` lines) or `ui: []`'
                )
            continue

        # A mis-cased top-level ui key is almost certainly a typo for `ui:`.
        miscased = re.match(r"^(UI|Ui|uI)\s*:", line)
        if miscased and not saw_key:
            warnings.append(
                f"Found a top-level '{miscased.group(1)}' key in {LANES_PATH}; the "
                "UI-lane key is lowercase 'ui:'. As written this repo declares no "
                "'ui:' block — fix the casing if a UI surface was intended."
            )

        if in_list:
            item = re.match(r"^\s*-\s*(.+?)\s*$", line)
            if item:
                value = item.group(1).strip().strip('"').strip("'")
                if value:
                    globs.append(value)
            elif not line[:1].isspace():
                in_list = False  # a new top-level key (e.g. non_device:) ends the list
    return globs, saw_key, warnings


def _glob_to_regex(glob):
    """Translate a path glob to a regex.

    ``**`` matches across directory separators (any depth); ``*`` matches within
    a single path segment; ``?`` matches one non-separator character.

    ``**/`` translates to *zero or more complete path segments* (``(?:.*/)?``),
    not a bare ``.*`` — otherwise a directory name after ``**/`` could match a
    *suffix* of another directory (``app/**/ui/**`` matching ``app/notui/…``).
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
                    out.append("(?:.*/)?")  # zero or more whole segments
                else:
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


def ui_paths(changed_files, ui_globs):
    """Changed files that match a ``ui:`` glob (the UI surface).

    The PR is on the UI lane when this list is non-empty.
    """
    return [
        path
        for path in changed_files
        if any(glob_match(path, glob) for glob in ui_globs)
    ]


def heuristic_ui_paths(changed_files):
    """Changed files that look like UI under the Phase-1 fallback heuristic."""
    return [
        path
        for path in changed_files
        if any(glob_match(path, glob) for glob in HEURISTIC_UI_GLOBS)
    ]


def is_web_path(path):
    """True if a path looks like a web UI file (scopes the web-only TYPE-03)."""
    return any(glob_match(path, glob) for glob in HEURISTIC_WEB_GLOBS)


def _gh_get(path):
    token = os.environ.get("GH_TOKEN", "")
    req = urllib.request.Request(GITHUB_API + path)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# GitHub caps the PR-files endpoint at 3000 files; past that the list is
# truncated. A truncated list could hide a UI file and skip the gate, so the
# caller treats "hit the cap" as indeterminable and fails safe to required.
GITHUB_PR_FILES_CAP = 3000


def fetch_changed_files(repo, pr_number):
    """Return ``(files, truncated)`` for the PR (paginated).

    A renamed file reports both its new ``filename`` and ``previous_filename``,
    so moving a file into or out of a UI glob still surfaces both paths.
    ``truncated`` is ``True`` if the PR has more files than the API will list
    (GitHub's 3000-file cap), so the surface cannot be trusted as complete.
    """
    files = []
    page = 1
    seen = 0
    while True:
        batch = _gh_get(
            f"/repos/{repo}/pulls/{pr_number}/files?per_page=100&page={page}"
        )
        if not batch:
            break
        for item in batch:
            files.append(item["filename"])
            previous = item.get("previous_filename")
            if previous:
                files.append(previous)
        seen += len(batch)
        if len(batch) < 100:
            break
        if seen >= GITHUB_PR_FILES_CAP:
            return files, True
        page += 1
    return files, False


def fetch_ui_globs(repo, ref):
    """Read the ``ui:`` declaration from thorne-lanes.yml at ``ref`` on ``repo``.

    Returns ``(globs, saw_ui_key, warnings)`` (see :func:`parse_ui_globs`).
    Reads from the PR base ref (not head) so a PR cannot narrow its own UI
    surface by editing the lanes file in the same PR. A missing file means no
    declared UI surface (Phase-1 fallback): ``([], False, [])``.
    """
    try:
        data = _gh_get(f"/repos/{repo}/contents/{LANES_PATH}?ref={ref}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return [], False, []
        raise
    content = base64.b64decode(data.get("content", "")).decode("utf-8")
    return parse_ui_globs(content)


def determine_ui_surface():
    """Return ``(is_ui, is_web, triggering, messages)``.

    * ``is_ui`` — the PR touches a UI surface (or the surface is indeterminable,
      fail-safe to the stricter, required path).
    * ``is_web`` — a web path is in the surface, so the web-only item is
      required. ``True`` on every fail-safe path (web-ness is unknown).
    * ``triggering`` — the changed files that put the PR on the UI lane (for an
      actionable message); ``None`` when the changed files could not be resolved.
    * ``messages`` — ``(level, text)`` pairs (``'warning'`` / ``'notice'``) that
      make the lane decision and any lanes-file ambiguity visible.
    """
    repo = os.environ.get("REPO", "").strip()
    pr_number = os.environ.get("PR_NUMBER", "").strip()
    base_ref = os.environ.get("BASE_REF", "").strip()

    if not (repo and pr_number and base_ref):
        return True, True, None, [
            (
                "notice",
                "PR context unavailable (need REPO, PR_NUMBER, and BASE_REF); "
                "requiring the Accessibility section (fail-safe).",
            )
        ]

    try:
        changed, truncated = fetch_changed_files(repo, pr_number)
    except Exception as exc:  # noqa: BLE001 — any API failure must fail safe to required
        return True, True, None, [
            (
                "warning",
                f"Could not fetch the PR's changed files ({exc}); requiring the "
                "Accessibility section (fail-safe).",
            )
        ]
    if truncated:
        return True, True, None, [
            (
                "warning",
                "This PR exceeds GitHub's 3000-file listing cap, so the UI "
                "surface cannot be determined completely; requiring the "
                "Accessibility section (fail-safe).",
            )
        ]
    if not changed:
        return True, True, None, [
            (
                "notice",
                "No changed files reported; requiring the Accessibility section "
                "(fail-safe).",
            )
        ]

    try:
        ui_globs, saw_key, warnings = fetch_ui_globs(repo, base_ref)
    except LanesError as exc:
        return True, True, None, [
            (
                "warning",
                f"Unparseable `ui:` block in {LANES_PATH} ({exc}); requiring the "
                "Accessibility section (fail-safe).",
            )
        ]
    except Exception as exc:  # noqa: BLE001 — any API failure must fail safe to required
        return True, True, None, [
            (
                "warning",
                f"Could not read {LANES_PATH} ({exc}); requiring the "
                "Accessibility section (fail-safe).",
            )
        ]

    messages = [("warning", text) for text in warnings]

    if saw_key:
        triggering = ui_paths(changed, ui_globs)
        source = "the repo's `ui:` block"
    else:
        triggering = heuristic_ui_paths(changed)
        source = "the Phase-1 file-path heuristic"
        messages.append(
            (
                "notice",
                f"No `ui:` block in {LANES_PATH}; using the Phase-1 file-path "
                "heuristic to resolve the UI surface (review-a11y SKILL.md § "
                "UI-surface determination). Add a `ui:` block to make the "
                "surface explicit.",
            )
        )

    if not triggering:
        messages.append(
            (
                "notice",
                f"No changed file is part of the UI surface (per {source}); "
                "accessibility not required.",
            )
        )
        return False, False, [], messages

    is_web = any(is_web_path(path) for path in triggering)
    return True, is_web, triggering, messages


def main():
    body = os.environ.get("PR_BODY")
    is_ui, is_web, triggering, messages = determine_ui_surface()
    required = required_item_ids(is_web)
    errors = validate_accessibility(body, required) if is_ui else []

    if is_ui:
        web_note = "web + native" if is_web else "native only"
        lane_label = f"ui (accessibility required — {web_note})"
    else:
        lane_label = "non-ui (accessibility not required)"

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("## Thorne A11y Check\n\n")
            handle.write(f"**Lane:** {lane_label}\n\n")
            for _level, text in messages:
                handle.write(f"_{text}_\n\n")
            if is_ui and triggering:
                handle.write(
                    "On the UI path because these changed files are part of the "
                    "UI surface:\n\n"
                )
                for path in triggering[:20]:
                    handle.write(f"- `{path}`\n")
                if len(triggering) > 20:
                    handle.write(f"- …and {len(triggering) - 20} more\n")
                handle.write("\n")
            if errors:
                handle.write("Failed checks:\n\n")
                for error in errors:
                    handle.write(f"- {error}\n")
            else:
                handle.write("Accessibility declaration is complete.\n")

    for level, text in messages:
        print(f"::{level}::{text}")
    if is_ui and triggering:
        shown = ", ".join(triggering[:10])
        if len(triggering) > 10:
            shown += f", and {len(triggering) - 10} more"
        print(f"::notice::UI path triggered by: {shown}")

    if errors:
        for error in errors:
            print(f"::error::{error}")
        sys.exit(1)

    print(
        f"Thorne accessibility declaration is complete (lane: {'ui' if is_ui else 'non-ui'})."
    )


if __name__ == "__main__":
    main()
