#!/usr/bin/env python3
"""Validate Thorne pull-request template boundary declarations.

Importable: ``validate(body) -> list[str]`` returns human-readable error
strings (empty list means the PR body satisfies the boundary declarations).

As a script: reads the PR body from ``PR_BODY``, writes a GitHub step
summary, emits ``::error::`` annotations, and exits non-zero on any failure.
"""

from __future__ import annotations

import os
import re
import sys

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

THORNE_SCOPE_ITEMS = {
    "Device function",
    "Non-device function",
    "Multiple-Function impact assessment",
    "Pre-design scaffolding under CMP §7",
    "DHF/QMS artifact",
    "Not Thorne-related",
}

SAFETY_CLASS_ITEMS = {
    "Class A",
    "Class B",
    "Class C",
    "C-adjacent integrity control",
    "N/A",
    "TBD / blocked until resolved",
}

# Boundary confirmations every Thorne-related PR must make.
MANDATORY_BOUNDARY_ITEMS = [
    "This PR does not introduce Eiro-authored clinical interpretation.",
    "This PR does not introduce safety detection, safety flagging, triage, crisis prediction, priority ranking, patient-status assignment, or treatment recommendation.",
    "This PR does not introduce PHQ-9 item 9 default alerting, urgent notification, 24-hour, push, or on-call alert behavior.",
    "This PR does not change the meaning, priority, salience, or safety significance of device output from a non-device surface.",
]

# Boundary confirmations required only for the scope that triggers them.
PRE_DESIGN_BOUNDARY_ITEMS = [
    "If this is pre-design scaffolding, it stays within CMP §7 and does not implement clinical device behavior.",
]

# Full set the template renders (used for checklist-completeness validation).
ALL_BOUNDARY_ITEMS = MANDATORY_BOUNDARY_ITEMS + PRE_DESIGN_BOUNDARY_ITEMS

# Scopes for which a substantive DHF Trace is mandatory.
DHF_TRACE_REQUIRED_SCOPES = {
    "Device function",
    "Multiple-Function impact assessment",
    "Pre-design scaffolding under CMP §7",
    "DHF/QMS artifact",
}

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
    return text.strip().lower()


def sections(markdown):
    """Map normalized ``## heading`` -> section body text."""
    found = {}
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", markdown))
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        found[normalize_heading(title)] = markdown[start:end].strip()
    return found


def checked_items(section_text):
    checked = set()
    for line in section_text.splitlines():
        match = re.match(r"^\s*-\s+\[[xX]\]\s+(.+?)\s*$", line)
        if match:
            checked.add(match.group(1).strip())
    return checked


def present_items(section_text):
    present = set()
    for line in section_text.splitlines():
        match = re.match(r"^\s*-\s+\[[ xX]\]\s+(.+?)\s*$", line)
        if match:
            present.add(match.group(1).strip())
    return present


def substantive_text(section_text):
    """Section text with HTML comments and checkbox lines removed."""
    cleaned = []
    for line in section_text.splitlines():
        line = re.sub(r"<!--.*?-->", "", line).strip()
        if not line:
            continue
        if line.startswith("- ["):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def validate(body):
    """Return a list of declaration errors for the given PR body."""
    body = body or ""
    parsed = sections(body)
    errors = []

    for section in REQUIRED_SECTIONS:
        if normalize_heading(section) not in parsed:
            errors.append(f"Missing required section: ## {section}")

    checkbox_expected = {
        "Thorne Scope": THORNE_SCOPE_ITEMS,
        "Safety Class": SAFETY_CLASS_ITEMS,
        "Thorne Boundary Check": set(ALL_BOUNDARY_ITEMS),
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

    thorne_scopes = scope_checked - {"Not Thorne-related"}
    not_thorne = "Not Thorne-related" in scope_checked
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

        if "Device function" in scope_checked:
            non_na_safety = safety_checked - {"N/A"}
            if not non_na_safety:
                errors.append(
                    "Device-function PRs must select at least one Safety Class item other than N/A."
                )

        for item in MANDATORY_BOUNDARY_ITEMS:
            if item not in boundary_checked:
                errors.append(f"Thorne-related PRs must confirm boundary item: {item}")

        if "Pre-design scaffolding under CMP §7" in scope_checked:
            for item in PRE_DESIGN_BOUNDARY_ITEMS:
                if item not in boundary_checked:
                    errors.append(f"Pre-design scaffolding PRs must confirm boundary item: {item}")

    return errors


def main():
    errors = validate(os.environ.get("PR_BODY"))

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            if errors:
                handle.write("## Thorne PR Boundary Check\n\nFailed checks:\n\n")
                for error in errors:
                    handle.write(f"- {error}\n")
            else:
                handle.write(
                    "## Thorne PR Boundary Check\n\nAll required PR boundary declarations are present.\n"
                )

    if errors:
        for error in errors:
            print(f"::error::{error}")
        sys.exit(1)

    print("Thorne PR boundary declarations are complete.")


if __name__ == "__main__":
    main()
