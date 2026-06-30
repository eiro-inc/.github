#!/usr/bin/env python3
"""Inject the Thorne PR template into device-lane Dependabot PRs.

Dependabot ignores ``.github/pull_request_template.md``, so its PRs arrive with
no Thorne boundary sections. The boundary check auto-approves *non-device*
Dependabot PRs (the lane assignment is the classification), so nothing needs to
be injected there. A *device*-lane Dependabot PR (a dependency/SOUP change) does
need human classification, so this injects the org template UNCHECKED for the
reviewer to fill in — "the consuming Thorne pull request is the control point for
classification" (CMP §85).

Env, supplied by the composite action: GH_TOKEN, REPO, PR_NUMBER, BASE_REF,
MARKER. Idempotent: a body already carrying MARKER is left untouched.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOUNDARY_PATH = os.path.join(HERE, "..", "thorne-pr-boundary-check", "thorne_pr_boundary_check.py")
TEMPLATE_PATH = os.path.join(HERE, "..", "..", "pull_request_template.md")
MARKER_DEFAULT = "<!-- thorne-boundary-block -->"
NOTE = (
    "> _Auto-injected: this Dependabot PR is on the device lane, "
    "so classify the template below before merge."
)


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def _load_boundary():
    """Import the sibling thorne-pr-boundary-check module from the same checkout."""
    spec = importlib.util.spec_from_file_location("thorne_pr_boundary_check", BOUNDARY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_body(original, marker, note, template):
    """Original Dependabot body, then the marker + note + unchecked template."""
    original = (original or "").strip()
    head = f"{original}\n\n" if original else ""
    return f"{head}{marker}\n\n{note}\n\n{template}\n"


def has_required_sections(boundary, body):
    """True if ``body`` already contains every Thorne template section."""
    parsed = boundary.sections(body or "")
    return all(
        boundary.normalize_heading(section) in parsed
        for section in boundary.REQUIRED_SECTIONS
    )


def main():
    boundary = _load_boundary()
    lane, _triggering, _note = boundary.determine_lane()
    if lane != "device":
        print(f"Lane is '{lane}'; the boundary check handles it. Nothing to inject.")
        return 0

    repo = os.environ["REPO"]
    pr_number = os.environ["PR_NUMBER"]
    marker = os.environ.get("MARKER", MARKER_DEFAULT)

    body = gh("pr", "view", pr_number, "--repo", repo, "--json", "body", "--jq", '.body // ""')
    if marker in body or has_required_sections(boundary, body):
        print("Marker present — template already injected; nothing to do.")
        return 0

    with open(TEMPLATE_PATH, encoding="utf-8") as handle:
        template = handle.read().strip()
    new_body = build_body(body, marker, NOTE, template)

    with open("/tmp/_thorne_new_body.md", "w", encoding="utf-8") as handle:
        handle.write(new_body)
    gh("pr", "edit", pr_number, "--repo", repo, "--body-file", "/tmp/_thorne_new_body.md")
    print(f"::notice::Injected device-lane Thorne template into {repo}#{pr_number} for classification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
