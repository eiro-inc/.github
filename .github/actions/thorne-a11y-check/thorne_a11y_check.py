#!/usr/bin/env python3
"""Validate the Thorne pull-request ``## Accessibility`` declaration.

Accessibility cuts the **UI / non-UI axis** — a *different* axis from the
device / non-device lanes enforced by ``thorne-pr-boundary-check``. The two
gates are siblings: neither subsumes the other, and a single PR may be both
device (full boundary block) and UI (accessibility block).

Two lanes, chosen automatically from the files a PR changes:

* **ui** — any changed file that matches a ``ui:`` glob in the repo's
  ``.github/thorne-lanes.yml`` puts the PR on the UI path, which requires the
  template's ``## Accessibility`` section to be filled (:func:`validate_accessibility`).
  ``ui:`` is an **allowlist**: nothing is UI by default (the inverse of the
  ``non_device:`` carve-out list the boundary check reads from the same file).
* **non-ui** — when *no* changed file matches a ``ui:`` glob, the PR takes the
  light path and the accessibility section is not required.

Importable pure helpers: ``validate_accessibility`` (body -> error list),
``parse_ui_globs``, ``glob_match``, ``ui_paths``.

As a script: reads ``PR_BODY`` plus ``REPO`` / ``PR_NUMBER`` / ``BASE_REF`` /
``GH_TOKEN``, determines the lane from the PR's changed files and the lanes
file on the base branch, writes a GitHub step summary, emits annotations, and
exits non-zero on failure. Fail-safe: if the UI surface cannot be determined,
the accessibility section is required (the stricter path).
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

# A checkbox item's stable ID, e.g. "SR-01" / "FORM-01" / "COLOR-03".
_ITEM_ID_RE = re.compile(r"\b([A-Z]{2,6}-\d{2})\b")

# Distinguishing substrings (lowercased) for the two lead checkboxes. Matched as
# substrings rather than exact text so incidental rewording of the surrounding
# phrasing does not disarm the lane selector.
_LEAD_CHANGES_UI = "changes user-facing ui"
_LEAD_NA = "no user-facing ui change"


def collapse_whitespace(text):
    """Collapse internal whitespace runs to a single space and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_heading(text):
    return collapse_whitespace(text).lower()


def sections(markdown):
    """Map normalized ``## heading`` -> section body text.

    ATX headings only at column 0 with a literal space/tab after ``##`` — the
    same strict rule the boundary check uses, so an indented ``##`` inside a
    list or an example heading cannot forge the section. The template renders
    ``## Accessibility`` at column 0 inside its ``<details>`` wrapper, so it is
    picked up; the trailing ``</details>`` is ignored (not a checkbox line).
    """
    found = {}
    matches = list(re.finditer(r"(?m)^##[ \t]+(.+?)[ \t]*$", markdown))
    for index, match in enumerate(matches):
        title = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        found[normalize_heading(title)] = markdown[start:end].strip()
    return found


def present_items(section_text):
    """Collapsed text of every checkbox line (ticked or not)."""
    present = set()
    for line in section_text.splitlines():
        match = re.match(r"^\s*-\s+\[[ xX]\]\s+(.+?)\s*$", line)
        if match:
            present.add(collapse_whitespace(match.group(1)))
    return present


def checked_items(section_text):
    """Collapsed text of every ticked (``[x]``) checkbox line."""
    checked = set()
    for line in section_text.splitlines():
        match = re.match(r"^\s*-\s+\[[xX]\]\s+(.+?)\s*$", line)
        if match:
            checked.add(collapse_whitespace(match.group(1)))
    return checked


def _has(items, needle):
    return any(needle in item.lower() for item in items)


def item_ids(items):
    """Stable IDs found across a set of checkbox-item texts."""
    ids = set()
    for item in items:
        ids.update(_ITEM_ID_RE.findall(item))
    return ids


def validate_accessibility(body):
    """Return a list of declaration errors for the ``## Accessibility`` section.

    Called only on the UI lane. Requires:

    * the ``## Accessibility`` section to be present;
    * both lead checkboxes present, with exactly one ticked (XOR);
    * ``N/A`` ticked -> pass (a touched UI file may still be a non-user-facing
      change; the reviewer owns that call, mirroring how the boundary gate
      trusts the declared scope);
    * ``changes user-facing UI`` ticked -> every human item present *and* ticked.
    """
    body = body or ""
    if not body.strip():
        return [
            "PR body is empty. This PR changes user-facing UI — fill the "
            "## Accessibility section of the Thorne PR template (WCAG 2.2 AA)."
        ]
    parsed = sections(body)
    text = parsed.get(normalize_heading(ACCESSIBILITY_SECTION))
    if text is None:
        return [
            "Missing required section: ## Accessibility. This PR changes "
            "user-facing UI; fill the accessibility checklist (WCAG 2.2 AA)."
        ]

    present = present_items(text)
    checked = checked_items(text)
    errors = []

    if not _has(present, _LEAD_CHANGES_UI):
        errors.append(
            "## Accessibility is missing the lead checkbox "
            "'This PR changes user-facing UI'."
        )
    if not _has(present, _LEAD_NA):
        errors.append(
            "## Accessibility is missing the lead checkbox "
            "'N/A — no user-facing UI change'."
        )

    changes_ui = _has(checked, _LEAD_CHANGES_UI)
    na = _has(checked, _LEAD_NA)
    if not (changes_ui or na):
        errors.append(
            "Tick exactly one Accessibility lead box: 'This PR changes "
            "user-facing UI' or 'N/A — no user-facing UI change'."
        )
    if changes_ui and na:
        errors.append(
            "Do not tick both Accessibility lead boxes; choose 'changes "
            "user-facing UI' or 'N/A'."
        )

    if changes_ui and not na:
        present_ids = item_ids(present)
        checked_ids = item_ids(checked)
        missing = [i for i in HUMAN_ITEM_IDS if i not in present_ids]
        if missing:
            errors.append(
                "## Accessibility is missing checklist item(s): "
                + ", ".join(missing)
                + "."
            )
        unconfirmed = [
            i for i in HUMAN_ITEM_IDS if i in present_ids and i not in checked_ids
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


def parse_ui_globs(yaml_text):
    """Extract the ``ui:`` list from a (minimal) thorne-lanes.yml.

    Understands the documented block shape only::

        ui:
          - "glob"
          - glob

    Comments and blank lines are ignored. Returns ``[]`` when the key is absent
    or empty — i.e., the repo declares no UI surface (accessibility never
    required). This mirrors ``parse_non_device_globs`` in the boundary check,
    reading a *different* key from the same file: the two axes coexist in one
    lanes file.
    """
    globs = []
    in_list = False
    for raw in (yaml_text or "").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if re.match(r"^ui\s*:\s*\[\s*\]\s*$", line):
            # Explicit empty list: declares no UI surface. Must NOT open block
            # mode, or a trailing "- glob" would be misread as a UI glob.
            continue
        if re.match(r"^ui\s*:\s*$", line):
            in_list = True
            continue
        if in_list:
            match = re.match(r"^\s*-\s*(.+?)\s*$", line)
            if match:
                value = match.group(1).strip().strip('"').strip("'")
                if value:
                    globs.append(value)
            elif not line[:1].isspace():
                in_list = False  # a new top-level key (e.g. non_device:) ends the list
    return globs


def _glob_to_regex(glob):
    """Translate a path glob to a regex.

    ``**`` matches across directory separators (any depth); ``*`` matches within
    a single path segment; ``?`` matches one non-separator character. Identical
    semantics to the boundary check's glob engine.
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


def ui_paths(changed_files, ui_globs):
    """Changed files that match a ``ui:`` glob (the UI surface).

    The PR is on the UI lane when this list is non-empty.
    """
    return [
        path
        for path in changed_files
        if any(glob_match(path, glob) for glob in ui_globs)
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

    A renamed file reports both its new ``filename`` and ``previous_filename``,
    so moving a file into or out of a UI glob still surfaces both paths.
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


def fetch_ui_globs(repo, ref):
    """Read ``ui:`` globs from thorne-lanes.yml at ``ref`` on ``repo``.

    Reads from the PR base ref (not head) so a PR cannot narrow its own UI
    surface by editing the lanes file in the same PR. A missing file means no
    declared UI surface.
    """
    try:
        data = _gh_get(f"/repos/{repo}/contents/{LANES_PATH}?ref={ref}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        raise
    content = base64.b64decode(data.get("content", "")).decode("utf-8")
    return parse_ui_globs(content)


def determine_ui_surface():
    """Return ``(is_ui, triggering_paths, note)``.

    ``is_ui`` is ``True`` when the PR touches a declared UI surface (or when the
    surface cannot be determined — fail-safe to the stricter, required path).
    ``triggering_paths`` lists the changed files matching a ``ui:`` glob (for an
    actionable message); ``None`` means the changed files could not be resolved.
    """
    repo = os.environ.get("REPO", "").strip()
    pr_number = os.environ.get("PR_NUMBER", "").strip()
    base_ref = os.environ.get("BASE_REF", "").strip()

    if not (repo and pr_number):
        return True, None, "PR context unavailable; requiring the Accessibility section (fail-safe)."
    try:
        changed = fetch_changed_files(repo, pr_number)
        globs = fetch_ui_globs(repo, base_ref) if base_ref else []
    except Exception as exc:  # noqa: BLE001 — any API failure must fail safe to required
        return True, None, f"Could not determine UI surface ({exc}); requiring the Accessibility section (fail-safe)."

    if not changed:
        return True, None, "No changed files reported; requiring the Accessibility section (fail-safe)."
    triggering = ui_paths(changed, globs)
    if triggering:
        return True, triggering, ""
    return False, [], ""


def main():
    body = os.environ.get("PR_BODY")
    is_ui, triggering, note = determine_ui_surface()
    errors = validate_accessibility(body) if is_ui else []

    lane_label = "ui (accessibility required)" if is_ui else "non-ui (accessibility not required)"
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("## Thorne A11y Check\n\n")
            handle.write(f"**Lane:** {lane_label}\n\n")
            if note:
                handle.write(f"_{note}_\n\n")
            if is_ui and triggering:
                handle.write(
                    "On the UI path because these changed files match a `ui:` glob "
                    "in `.github/thorne-lanes.yml`:\n\n"
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

    if note:
        print(f"::notice::{note}")
    if is_ui and triggering:
        shown = ", ".join(triggering[:10])
        if len(triggering) > 10:
            shown += f", and {len(triggering) - 10} more"
        print(f"::notice::UI path triggered by: {shown}")

    if errors:
        for error in errors:
            print(f"::error::{error}")
        sys.exit(1)

    print(f"Thorne accessibility declaration is complete (lane: {'ui' if is_ui else 'non-ui'}).")


if __name__ == "__main__":
    main()
