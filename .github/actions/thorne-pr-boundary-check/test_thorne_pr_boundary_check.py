"""Unit tests for the Thorne PR boundary-check validator."""

from thorne_pr_boundary_check import (
    ALL_BOUNDARY_ITEMS,
    MANDATORY_BOUNDARY_ITEMS,
    SAFETY_CLASS_ITEMS,
    THORNE_SCOPE_ITEMS,
    validate,
)


def _checklist(all_items, checked):
    checked = set(checked)
    return "\n".join(f"- [{'x' if item in checked else ' '}] {item}" for item in all_items)


def make_body(
    scopes=(),
    safety=(),
    boundary_checked=ALL_BOUNDARY_ITEMS,
    dhf_trace="DDS §5",
    drop_sections=(),
):
    blocks = {
        "Summary": "A change.",
        "Related Issue": "Closes #1",
        "Thorne Scope": _checklist(sorted(THORNE_SCOPE_ITEMS), scopes),
        "DHF Trace": dhf_trace,
        "Safety Class": _checklist(sorted(SAFETY_CLASS_ITEMS), safety),
        "Verification": "- [x] DHF document review only",
        "Thorne Boundary Check": _checklist(ALL_BOUNDARY_ITEMS, boundary_checked),
        "Reviewer Notes": "None.",
    }
    return "\n\n".join(
        f"## {title}\n\n{body}" for title, body in blocks.items() if title not in drop_sections
    )


def test_valid_device_pr_passes():
    body = make_body(["Device function"], ["Class B"], MANDATORY_BOUNDARY_ITEMS, "DDS §5; SRS-02-04")
    assert validate(body) == []


def test_missing_section_is_flagged():
    body = make_body(["Non-device function"], drop_sections=["Reviewer Notes"])
    assert any("Missing required section: ## Reviewer Notes" == e for e in validate(body))


def test_untouched_html_comment_trace_fails_for_device():
    body = make_body(
        ["Device function"],
        ["Class B"],
        MANDATORY_BOUNDARY_ITEMS,
        "<!-- Cite controlling anchors: CMP §7, DDS §5/§6/§7, UNS, SRS, SDD, HAZ, TRM, DR, etc. -->",
    )
    assert any("DHF Trace" in e for e in validate(body))


def test_freeform_text_without_anchor_fails():
    body = make_body(["Device function"], ["Class B"], MANDATORY_BOUNDARY_ITEMS, "TBD, will fill in later")
    assert any("DHF Trace" in e for e in validate(body))


def test_dds_section_reference_is_accepted():
    body = make_body(["Device function"], ["Class B"], MANDATORY_BOUNDARY_ITEMS, "Traces to DDS §5.")
    assert validate(body) == []


def test_numbered_dhf_ids_are_accepted():
    # Anchors the reviewer's narrower regex would have wrongly rejected.
    for trace in ("SRS-02-04", "HAZ-3", "UNS-12 and SDD-4", "TRM"):
        body = make_body(["Device function"], ["Class B"], MANDATORY_BOUNDARY_ITEMS, trace)
        assert validate(body) == [], f"expected {trace!r} to satisfy the anchor check"


def test_device_function_requires_non_na_safety_class():
    body = make_body(["Device function"], ["N/A"], MANDATORY_BOUNDARY_ITEMS, "DDS §5")
    assert any("Safety Class" in e for e in validate(body))


def test_non_device_pr_does_not_require_dhf_trace():
    body = make_body(["Non-device function"], boundary_checked=MANDATORY_BOUNDARY_ITEMS, dhf_trace="<!-- n/a -->")
    assert validate(body) == []


def test_missing_mandatory_boundary_item_fails():
    body = make_body(
        ["Non-device function"],
        boundary_checked=MANDATORY_BOUNDARY_ITEMS[:-1],
        dhf_trace="<!-- n/a -->",
    )
    assert any("must confirm boundary item" in e for e in validate(body))


def test_pre_design_requires_pre_design_boundary_item():
    without = make_body(
        ["Pre-design scaffolding under CMP §7"],
        boundary_checked=MANDATORY_BOUNDARY_ITEMS,
        dhf_trace="CMP §7",
    )
    assert any("Pre-design scaffolding PRs must confirm" in e for e in validate(without))

    with_item = make_body(
        ["Pre-design scaffolding under CMP §7"],
        boundary_checked=ALL_BOUNDARY_ITEMS,
        dhf_trace="CMP §7",
    )
    assert validate(with_item) == []


def test_not_thorne_related_alone_passes():
    body = make_body(["Not Thorne-related"], boundary_checked=[], dhf_trace="<!-- none -->")
    assert validate(body) == []


def test_not_thorne_combined_with_device_fails():
    body = make_body(
        ["Not Thorne-related", "Device function"],
        ["Class B"],
        MANDATORY_BOUNDARY_ITEMS,
        "DDS §5",
    )
    assert any("Not Thorne-related" in e for e in validate(body))
