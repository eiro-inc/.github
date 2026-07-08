"""Unit tests for the Thorne PR boundary-check validator."""

import pathlib
import urllib.error

import pytest

from thorne_pr_boundary_check import (
    ALL_BOUNDARY_ITEMS,
    MANDATORY_BOUNDARY_ITEMS,
    SAFETY_CLASS_ITEMS,
    THORNE_SCOPE_ITEMS,
    determine_lane,
    device_paths,
    fetch_changed_files,
    fetch_non_device_globs,
    glob_match,
    is_whitelisted,
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


# --- Whitespace tolerance: wording matches regardless of spacing ---

def test_extra_whitespace_in_checklist_items_still_matches():
    # Double spaces and tabs inside an item must not break the match: the gate
    # keys on wording, not exact spacing.
    body = make_body(["Device function"], ["Class B"], MANDATORY_BOUNDARY_ITEMS, "DDS §5")
    body = body.replace("- [x] Class B", "- [x] Class  B")
    body = body.replace("- [x] Device function", "- [x] Device\tfunction")
    assert validate(body) == []


def test_reflowed_boundary_item_still_confirmed():
    # A long boundary sentence that picked up an extra space still counts as
    # confirmed once whitespace is collapsed.
    body = make_body(["Non-device function"], boundary_checked=MANDATORY_BOUNDARY_ITEMS, dhf_trace="<!-- n/a -->")
    original = MANDATORY_BOUNDARY_ITEMS[0]
    body = body.replace(original, original.replace(" ", "  ", 1))
    assert validate(body) == []


def test_extra_whitespace_in_heading_still_discovered():
    body = make_body(["Non-device function"], boundary_checked=MANDATORY_BOUNDARY_ITEMS, dhf_trace="<!-- n/a -->")
    body = body.replace("## Reviewer Notes", "##   Reviewer   Notes")
    assert validate(body) == []


def test_indented_heading_does_not_hijack_real_section():
    # An indented ``## Thorne Boundary Check`` (e.g. a template example inside
    # Reviewer Notes) is list-continuation text, not a heading. It must not
    # overwrite the real section: a body whose real Boundary Check is missing a
    # mandatory confirmation still fails, even when a fully-ticked indented
    # duplicate follows it.
    body = make_body(
        ["Non-device function"],
        boundary_checked=MANDATORY_BOUNDARY_ITEMS[:-1],  # real section left incomplete
        dhf_trace="<!-- n/a -->",
    )
    decoy = "   ## Thorne Boundary Check\n\n" + _checklist(ALL_BOUNDARY_ITEMS, ALL_BOUNDARY_ITEMS)
    body = f"{body}\n\n{decoy}"
    assert any("must confirm boundary item" in e for e in validate(body))


def test_nbsp_after_hashes_is_not_a_heading():
    # ``##`` + non-breaking space renders as plain text on GitHub, not a
    # heading, so it must not satisfy the required-section check (fail-open).
    body = make_body(["Non-device function"], boundary_checked=MANDATORY_BOUNDARY_ITEMS, dhf_trace="<!-- n/a -->")
    body = body.replace("## Reviewer Notes", "##\u00a0Reviewer Notes")
    assert any("Missing required section: ## Reviewer Notes" == e for e in validate(body))


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


def test_parse_non_device_globs_explicit_empty_list_does_not_open_block():
    # `non_device: []` declares no carve-outs; a (malformed) trailing dash line
    # must not be read as one, even though a real YAML parser would reject it.
    assert parse_non_device_globs("non_device: []\n  - docs/**\n") == []
    assert parse_non_device_globs("non_device: [ ]\n  - docs/**\n") == []


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


def test_glob_question_mark_matches_one_non_separator_char():
    assert glob_match("src/a.ts", "src/?.ts")
    assert not glob_match("src/ab.ts", "src/?.ts")  # ? is exactly one char
    assert not glob_match("a/c", "a?c")  # ? does not cross a separator


def test_glob_match_empty_or_whitespace_glob_is_false():
    for empty in ("", "   ", None):
        assert not glob_match("docs/x.md", empty)


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


def test_no_changed_files_has_no_device_paths():
    assert device_paths([], ["docs/**"]) == []


def test_determine_lane_fails_safe_when_no_changed_files(monkeypatch):
    monkeypatch.setenv("REPO", "eiro-inc/thorne-core")
    monkeypatch.setenv("PR_NUMBER", "1")
    monkeypatch.setenv("BASE_REF", "main")
    monkeypatch.setattr("thorne_pr_boundary_check.fetch_changed_files", lambda repo, pr: [])
    monkeypatch.setattr("thorne_pr_boundary_check.fetch_non_device_globs", lambda repo, ref: ["docs/**"])

    lane, triggering, note = determine_lane()

    assert lane == "device"
    assert triggering is None  # unknown, not empty: the dependency check must not silently pass
    assert "No changed files reported" in note


def test_fetch_changed_files_includes_rename_old_path(monkeypatch):
    # A rename is one API entry: new path in `filename`, old path in
    # `previous_filename`. Both must surface, so moving a device file into a
    # carve-out still puts the old device path on the device lane.
    batch = [
        {
            "filename": "docs/lib.rs",
            "status": "renamed",
            "previous_filename": "crates/scoring/lib.rs",
        },
        {"filename": "src/app.ts", "status": "modified"},
    ]
    monkeypatch.setattr("thorne_pr_boundary_check._gh_get", lambda path: batch)

    files = fetch_changed_files("eiro-inc/thorne-core", "7")

    assert "docs/lib.rs" in files
    assert "crates/scoring/lib.rs" in files  # old path of the rename
    assert "src/app.ts" in files
    # the old device path forces the device lane even under a docs/** carve-out
    assert "crates/scoring/lib.rs" in device_paths(files, ["docs/**"])


def test_fetch_non_device_globs_returns_empty_when_lanes_file_missing(monkeypatch):
    # No thorne-lanes.yml is the common early-adopter case: 404 -> no carve-outs.
    def raise_404(path):
        raise urllib.error.HTTPError(path, 404, "Not Found", {}, None)

    monkeypatch.setattr("thorne_pr_boundary_check._gh_get", raise_404)
    assert fetch_non_device_globs("eiro-inc/thorne-core", "main") == []


def test_fetch_non_device_globs_reraises_non_404(monkeypatch):
    # A real fetch error must not be swallowed into "no carve-outs"; determine_lane
    # catches it and fails safe to the device lane.
    def raise_500(path):
        raise urllib.error.HTTPError(path, 500, "Server Error", {}, None)

    monkeypatch.setattr("thorne_pr_boundary_check._gh_get", raise_500)
    with pytest.raises(urllib.error.HTTPError):
        fetch_non_device_globs("eiro-inc/thorne-core", "main")


# --- Light-lane validation ---

def test_validate_light_requires_nonempty_summary():
    assert validate_light("## Summary\n\nDid a thing.") == []
    assert validate_light("## Summary\n\n") != []
    assert validate_light("") != []


# --- Non-device actor whitelist ---

def test_is_whitelisted_recognizes_automation_logins():
    assert is_whitelisted("dependabot[bot]")
    assert not is_whitelisted("test-eiro")
    assert not is_whitelisted("")
    assert not is_whitelisted(None)


def test_validate_light_whitelists_whitelisted_actor():
    # A raw bot body (no Summary) would fail the Summary requirement; a whitelisted
    # actor passes anyway, because reaching the non_device lane already proves
    # every changed file is a declared non-device path.
    assert validate_light("", "dependabot[bot]") == []
    assert validate_light(None, "dependabot[bot]") == []


def test_validate_light_non_whitelisted_actor_still_needs_summary():
    assert validate_light("", "test-eiro") != []
    assert validate_light("## Summary\n\nA change.", "test-eiro") == []
    # default (no actor) is the non-whitelisted path
    assert validate_light("") != []


# --- Shipped org PR template parses through the validator ---
# .github/actions/thorne-pr-boundary-check/<this file> -> .github/pull_request_template.md
_TEMPLATE_PATH = pathlib.Path(__file__).resolve().parents[2] / "pull_request_template.md"


def _org_template():
    return _TEMPLATE_PATH.read_text(encoding="utf-8")


def test_org_template_sections_are_all_discoverable():
    # Device sections live inside a <details> block; sections() must still find
    # every required heading. Guards against a template edit that breaks parsing.
    errors = validate(_org_template())
    assert not any(e.startswith("Missing required section") for e in errors)


def test_filled_org_template_passes_device_validation():
    # Fill the shipped template as a coherent device PR and confirm validate()
    # accepts it — so a future structural edit can't silently break the gate.
    body = _org_template()
    for item in ("Device function", "Class B", *MANDATORY_BOUNDARY_ITEMS):
        body = body.replace(f"- [ ] {item}", f"- [x] {item}")
    body = body.replace("## DHF Trace\n", "## DHF Trace\n\nTraces to DDS §5.\n")
    assert validate(body) == []


# --- New Dependencies (CMP §10) conditional check ---

from thorne_pr_boundary_check import (  # noqa: E402
    DEPENDENCY_CHECK_UNAVAILABLE,
    dependency_manifest_paths,
    determine_lane,
    validate_new_dependencies,
)


def test_untouched_org_template_fails_dependency_check():
    # Regression: the template's multi-line HTML comment must not count as a
    # substantive declaration (per-line stripping leaked its inner lines).
    assert validate_new_dependencies(_org_template(), ["package.json"])


def test_multiline_comment_alone_is_not_substantive():
    body = "## New Dependencies\n\n<!-- line one\n     line two\n     line three -->\n\n- None\n"
    assert validate_new_dependencies(body, ["package.json"])


def test_decorated_bare_none_variants_fail():
    for none_variant in ("*None*", "- None -", "None!", "none.", "_None_"):
        body = f"## New Dependencies\n\n{none_variant}\n"
        assert validate_new_dependencies(body, ["package.json"]), none_variant


def test_unknown_changed_files_reports_check_unavailable():
    # Fail-safe polarity: unknown changed files must not silently pass (None
    # sentinel from determine_lane's fallback paths), even with no body issue.
    messages = validate_new_dependencies("## New Dependencies\n\nfoo@1 — runtime\n", None)
    assert messages == [DEPENDENCY_CHECK_UNAVAILABLE]


def test_python_and_go_manifests_match():
    hits = dependency_manifest_paths(
        ["svc/pyproject.toml", "svc/requirements-dev.txt", "tool/go.mod", "tool/go.sum", "a/uv.lock"]
    )
    assert len(hits) == 5


def test_determine_lane_without_pr_context_reports_unknown_files(monkeypatch):
    for var in ("REPO", "PR_NUMBER", "BASE_REF"):
        monkeypatch.delenv(var, raising=False)
    lane, triggering, note = determine_lane()
    assert lane == "device"
    assert triggering is None
    assert note


def test_dependency_manifest_paths_matches_all_ecosystems():
    changed = [
        "svc-capture/package.json",
        "package-lock.json",
        "crates/thorne-app/Cargo.toml",
        "Cargo.lock",
        "app/build.gradle.kts",
        "gradle/libs.versions.toml",
        "gradle.lockfile",
        "thorne-ios/Package.resolved",
        "src/handler.ts",
        "docs/notes.md",
    ]
    hits = dependency_manifest_paths(changed)
    assert "src/handler.ts" not in hits
    assert "docs/notes.md" not in hits
    assert len(hits) == 8


def test_no_manifest_change_requires_nothing():
    assert validate_new_dependencies("anything", []) == []


def test_manifest_change_with_missing_section_fails():
    body = "## Summary\n\nAdds a package.\n"
    messages = validate_new_dependencies(body, ["package.json"])
    assert len(messages) == 1
    assert "New Dependencies" in messages[0]


def test_manifest_change_with_bare_none_fails():
    body = "## New Dependencies\n\n- None\n"
    assert validate_new_dependencies(body, ["Cargo.lock"])


def test_manifest_change_with_explained_none_passes():
    body = "## New Dependencies\n\n- None — lockfile refresh only, no dependency changes.\n"
    assert validate_new_dependencies(body, ["package-lock.json"]) == []


def test_manifest_change_with_declaration_passes():
    body = (
        "## New Dependencies\n\n"
        "- ulid@2.4.0 — runtime, device path (svc-capture) — ReportId generation — MIT — active\n"
    )
    assert validate_new_dependencies(body, ["svc-capture/package.json"]) == []


def test_template_comment_alone_is_not_substantive():
    body = "## New Dependencies\n\n<!-- list deps here -->\n"
    assert validate_new_dependencies(body, ["package.json"])
