"""Unit tests for the Thorne PR boundary-check validator."""

from thorne_pr_boundary_check import (
    ALL_BOUNDARY_ITEMS,
    MANDATORY_BOUNDARY_ITEMS,
    SAFETY_CLASS_ITEMS,
    THORNE_SCOPE_ITEMS,
    device_paths,
    glob_match,
    parse_non_device_globs,
    validate,
    validate_light,
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


def test_empty_body_returns_single_error():
    for body in ("", "   \n\t  ", None):
        errs = validate(body)
        assert errs == ["PR body is empty. Use the organization Thorne PR template."]


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


# --- Lane detection: parsing thorne-lanes.yml ---

def test_parse_non_device_globs_block_list():
    yml = (
        "# header comment\n"
        "non_device:\n"
        '  - "docs/**"\n'
        "  - src/ui/**   # trailing comment\n"
    )
    assert parse_non_device_globs(yml) == ["docs/**", "src/ui/**"]


def test_parse_non_device_globs_absent_or_empty_means_no_carveouts():
    assert parse_non_device_globs("") == []
    assert parse_non_device_globs(None) == []
    assert parse_non_device_globs("non_device: []\n") == []
    assert parse_non_device_globs("some_other_key:\n  - x\n") == []


def test_parse_non_device_globs_stops_at_next_top_level_key():
    yml = "non_device:\n  - docs/**\nother:\n  - not-a-glob\n"
    assert parse_non_device_globs(yml) == ["docs/**"]


# --- Lane detection: glob matching ---

def test_glob_double_star_matches_any_depth():
    assert glob_match("docs/a/b.md", "docs/**")
    assert glob_match("docs/x.md", "docs/**")
    assert not glob_match("src/docs.md", "docs/**")


def test_glob_single_star_is_segment_scoped():
    assert glob_match("src/a.ts", "src/*.ts")
    assert not glob_match("src/a/b.ts", "src/*.ts")


def test_glob_bare_path_is_treated_as_prefix():
    assert glob_match("src/ui/x.tsx", "src/ui")
    assert glob_match("src/ui", "src/ui")
    assert not glob_match("src/uikit/x", "src/ui")


# --- Lane detection: device-by-default decision ---

def test_device_by_default_when_no_carveouts():
    assert device_paths(["crates/scoring/lib.rs"], []) == ["crates/scoring/lib.rs"]


def test_light_when_every_file_is_carved_out():
    globs = ["docs/**", "src/ui/**"]
    assert device_paths(["docs/x.md", "src/ui/a.tsx"], globs) == []


def test_device_if_any_file_is_not_carved_out():
    globs = ["docs/**"]
    assert device_paths(["docs/x.md", "crates/scoring/lib.rs"], globs) == [
        "crates/scoring/lib.rs"
    ]


def test_no_changed_files_is_light():
    assert device_paths([], ["docs/**"]) == []


# --- Light-lane validation ---

def test_validate_light_requires_nonempty_summary():
    assert validate_light("## Summary\n\nDid a thing.") == []
    assert validate_light("## Summary\n\n") != []
    assert validate_light("") != []
