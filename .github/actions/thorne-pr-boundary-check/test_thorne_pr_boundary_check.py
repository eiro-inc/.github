"""Unit tests for the Thorne PR boundary-check validator."""

import importlib.util
import pathlib
import re
import sys
import types
import urllib.error

import pytest

from thorne_pr_boundary_check import (
    ALL_BOUNDARY_ITEMS,
    MANDATORY_BOUNDARY_ITEMS,
    SAFETY_CLASS_ITEMS,
    THORNE_SCOPE_ITEMS,
    DhfUnavailable,
    determine_lane,
    device_paths,
    dhf_anchor_candidates,
    fetch_changed_files,
    fetch_non_device_globs,
    glob_match,
    is_whitelisted,
    load_dhf_namespaces,
    main,
    normalize_anchor,
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


# --- DHF Trace anchor existence (thorne-dhf#113 AC2, issue #23) --------------


class FakeNamespaces:
    """Stand-in for ``vvtrace.namespaces.DhfNamespaces``.

    Mirrors the engine's id shapes (two-digit, zero-padded — the DHF uses no
    other form) so these tests run without the private engine installed. The
    real ``DhfNamespaces`` is exercised by the integration test below, which
    skips when the engine is absent.
    """

    # IFS-02-09a mirrors the real DHF, which does carry letter-suffixed IFS
    # items — the reason normalization must not uppercase the whole token.
    EXISTING = frozenset(
        {
            "SRS-02-04", "SRS-02", "SDD-01", "ARC-02",
            "IFS-09-01", "IFS-09", "IFS-02", "IFS-02-09a", "HAZ-26",
        }
    )
    SHAPES = (
        (r"SRS-\d{2}-\d{2}", "srs"),
        (r"IFS-\d{2}-\d{2}[a-z]?", "ifs"),
        (r"SDD-\d{2}", "sdd"),
        (r"ARC-\d{2}", "arc"),
        (r"IFS-\d{2}", "ifs-category"),
        (r"SRS-\d{2}", "srs-category"),
        (r"HAZ-\d{2}", "haz"),
    )

    def kind(self, anchor):
        for pattern, name in self.SHAPES:
            if re.fullmatch(pattern, anchor):
                return name
        return None

    def is_valid(self, anchor):
        return self.kind(anchor) is not None and anchor in self.EXISTING


def _device_body(trace):
    return make_body(["Device function"], ["Class B"], MANDATORY_BOUNDARY_ITEMS, trace)


def test_existing_dhf_ids_pass_the_existence_check():
    body = _device_body("Traces to SRS-02-04, SDD-01, HAZ-26.")
    assert validate(body, FakeNamespaces()) == []


def test_nonexistent_but_well_shaped_id_fails():
    body = _device_body("Traces to SRS-77-77.")
    errors = validate(body, FakeNamespaces())
    assert any("SRS-77-77" in e and "does not exist" in e for e in errors), errors


def test_nonexistent_id_passes_the_shape_only_check():
    """The gap AC2 closes: shape alone accepts an id that does not exist."""
    body = _device_body("Traces to SRS-77-77.")
    assert validate(body) == []


def test_malformed_id_of_a_checkable_family_is_reported():
    # The DHF writes zero-padded two-digit ids exclusively; HAZ-3 is not a real
    # id, and the engine cannot classify it. Report rather than silently skip.
    body = _device_body("Traces to HAZ-3.")
    errors = validate(body, FakeNamespaces())
    assert any("HAZ-3" in e and "well-formed" in e for e in errors), errors


def test_uncheckable_families_are_never_flagged():
    """The regression that would fail nearly every Thorne PR.

    ADR/CMP/DDS/TRM/SOP/§/CFR have no DHF namespace loader, so they must pass
    through untouched rather than being reported as unrecognized anchors.
    """
    for trace in (
        "DDS §5",
        "ADR-0002",
        "CMP §7",
        "SOP-013 §15",
        "TRM",
        "UNS-12",
        "21 CFR 820.30(g)",
        "ISO 14971",
        "VVP-01 and DR-02",
    ):
        body = _device_body(trace)
        assert validate(body, FakeNamespaces()) == [], f"{trace!r} should not be flagged"


def test_narrative_trace_behavior_is_unchanged_by_the_namespace():
    """Unshaped text fails the shape check, with or without existence checking."""
    body = _device_body("TBD, will fill in later")
    with_ns = validate(body, FakeNamespaces())
    without_ns = validate(body)
    assert with_ns == without_ns
    assert any("DHF Trace" in e for e in with_ns)


def test_mixed_trace_reports_only_the_bad_id():
    body = _device_body("DDS §5; SRS-02-04; SDD-99")
    errors = validate(body, FakeNamespaces())
    assert len(errors) == 1, errors
    assert "SDD-99" in errors[0] and "does not exist" in errors[0]


def test_each_bad_id_is_reported_once_even_if_cited_twice():
    body = _device_body("SDD-99 in one place and SDD-99 again")
    assert len(validate(body, FakeNamespaces())) == 1


def test_non_device_lane_is_unaffected():
    """validate_light has no DHF Trace requirement, so nothing to existence-check."""
    assert validate_light("## Summary\n\nA change.") == []


def test_anchor_candidates_only_picks_checkable_families():
    text = "SRS-02-04 ADR-0002 SDD-01 CMP §7 HAZ-26 SOP-013 IFS-09-01 ARC-02"
    assert dhf_anchor_candidates(text) == [
        "ARC-02",
        "HAZ-26",
        "IFS-09-01",
        "SDD-01",
        "SRS-02-04",
    ]


def test_prose_is_not_mistaken_for_an_id():
    """A digit must follow the family hyphen, so hyphenated prose flows."""
    for text in ("SRS-based approach", "haz-mat storage", "the ARC-shaped brief"):
        assert dhf_anchor_candidates(text) == [], text


# --- fail-open regressions reported in review (Codex) ------------------------


def test_lowercase_id_is_existence_checked_not_skipped():
    """ANCHOR_RE is case-insensitive; a case-only mismatch must not fail open.

    Uppercase-only candidate matching let 'srs-77-77' satisfy the shape test
    while producing no candidate, so the citation was accepted unvalidated.
    """
    assert dhf_anchor_candidates("srs-77-77") == ["srs-77-77"]
    errors = validate(_device_body("Traces to srs-77-77."), FakeNamespaces())
    assert any("srs-77-77" in e and "does not exist" in e for e in errors), errors


def test_lowercase_citation_of_a_real_id_passes():
    """Normalization is on the family prefix, so a real id is not failed on casing."""
    assert validate(_device_body("Traces to srs-02-04."), FakeNamespaces()) == []


def test_ifs_item_suffix_survives_normalization():
    """Uppercasing the whole token would break IFS-02-09a's lowercase suffix.

    The real DHF carries letter-suffixed IFS items (IFS-02-09a, IFS-04-04b),
    and the engine's IFS pattern requires that suffix lowercase.
    """
    assert normalize_anchor("ifs-02-09a") == "IFS-02-09a"
    assert normalize_anchor("IFS-02-09A") == "IFS-02-09A"  # not silently repaired
    assert validate(_device_body("Traces to ifs-02-09a."), FakeNamespaces()) == []


def test_overlong_token_is_not_truncated_to_a_valid_prefix():
    """'SRS-02-04-999' must not be read as the existing 'SRS-02-04'."""
    assert dhf_anchor_candidates("SRS-02-04-999") == ["SRS-02-04-999"]
    errors = validate(_device_body("Traces to SRS-02-04-999."), FakeNamespaces())
    assert any("SRS-02-04-999" in e and "well-formed" in e for e in errors), errors


def test_duplicate_citations_differing_only_in_case_report_once():
    body = _device_body("SDD-99 and sdd-99")
    assert len(validate(body, FakeNamespaces())) == 1


def test_standalone_arc_citation_satisfies_the_shape_check():
    """ARC was missing from ANCHOR_RE, so an ARC-only trace was rejected
    before existence validation could run — even for an ARC id that exists."""
    assert validate(_device_body("Traces to ARC-02."), FakeNamespaces()) == []


def test_standalone_nonexistent_arc_is_reported_as_missing():
    errors = validate(_device_body("Traces to ARC-99."), FakeNamespaces())
    assert any("ARC-99" in e and "does not exist" in e for e in errors), errors


def test_markdown_link_target_slug_is_not_a_citation():
    """GitHub heading slugs look like malformed ids; they are URL fragments.

    Real case, thorne-dhf#139: a DHF Trace linking to the document it cites
    carried '#ifs-02--patient-data-capture' in the link target, which a plain
    token scan reads as a malformed IFS id.
    """
    trace = "[IFS-02](https://github.com/eiro-inc/thorne-dhf/blob/main/02-inputs/IFS.md#ifs-02--patient-data-capture)"
    assert dhf_anchor_candidates(trace) == ["IFS-02"]
    assert validate(_device_body(trace), FakeNamespaces()) == []


def test_bare_url_containing_an_id_is_ignored():
    trace = "See https://github.com/eiro-inc/thorne-dhf/blob/main/04-outputs/SDD.md#sdd-99-widget and SDD-01."
    assert dhf_anchor_candidates(trace) == ["SDD-01"]
    assert validate(_device_body(trace), FakeNamespaces()) == []


def test_alpha_placeholder_remains_narrative_not_a_candidate():
    """Documented limitation: SRS-XX-YY is not a candidate (catching it would
    flag prose). Alone it still fails the shape check; only a trace that also
    carries a real anchor lets it through."""
    assert dhf_anchor_candidates("SRS-XX-YY") == []
    assert validate(_device_body("SRS-XX-YY"), FakeNamespaces())


# --- fail-safe ---------------------------------------------------------------


def test_load_dhf_namespaces_raises_when_engine_missing(monkeypatch):
    """A missing engine must raise, never return an empty namespace.

    An empty DhfNamespaces would classify every cited id as nonexistent and
    fail every PR; silently returning None would pass them all unverified.
    """
    import builtins

    real_import = builtins.__import__

    def no_vvtrace(name, *args, **kwargs):
        if name.startswith("vvtrace"):
            raise ImportError("No module named 'vvtrace'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_vvtrace)
    with pytest.raises(DhfUnavailable) as excinfo:
        load_dhf_namespaces("/nonexistent")
    assert "not importable" in str(excinfo.value)


def test_load_dhf_namespaces_raises_when_dhf_unreadable(tmp_path, monkeypatch):
    """Engine present, DHF absent (a failed fetch) — must raise, not pass."""
    fake = types.ModuleType("vvtrace")
    fake_ns = types.ModuleType("vvtrace.namespaces")

    def load_all(root):
        raise FileNotFoundError(f"{root}/02-inputs/SRS.md")

    fake_ns.load_all = load_all
    monkeypatch.setitem(sys.modules, "vvtrace", fake)
    monkeypatch.setitem(sys.modules, "vvtrace.namespaces", fake_ns)
    with pytest.raises(DhfUnavailable) as excinfo:
        load_dhf_namespaces(str(tmp_path / "missing"))
    assert "could not read the DHF" in str(excinfo.value)


def test_main_fails_the_check_when_dhf_unavailable(monkeypatch, capsys, tmp_path):
    """End-to-end fail-safe: DHF_ROOT set but unloadable -> non-zero exit."""
    body = _device_body("Traces to SRS-02-04.")
    monkeypatch.setenv("PR_BODY", body)
    monkeypatch.setenv("DHF_ROOT", str(tmp_path / "never-fetched"))
    monkeypatch.delenv("REPO", raising=False)
    monkeypatch.delenv("PR_NUMBER", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1
    out = capsys.readouterr().out
    assert "existence check could not run" in out


def test_main_passes_without_dhf_root(monkeypatch, capsys):
    """No opt-in: the body validates on shape alone and the check passes."""
    monkeypatch.setenv("PR_BODY", _device_body("Traces to SRS-77-77."))
    monkeypatch.delenv("DHF_ROOT", raising=False)
    monkeypatch.delenv("REPO", raising=False)
    monkeypatch.delenv("PR_NUMBER", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    main()
    assert "complete" in capsys.readouterr().out


# --- integration with the real engine (skipped when it is not installed) -----

@pytest.mark.skipif(
    importlib.util.find_spec("vvtrace") is None,
    reason="private vvtrace engine not installed",
)
def test_real_engine_namespace_shapes_match_the_fake():
    """Guard against the stub drifting from the engine it stands in for."""
    from vvtrace.namespaces import DhfNamespaces

    real = DhfNamespaces()
    fake = FakeNamespaces()
    for anchor in (
        "SRS-02-04", "SRS-02", "SDD-01", "ARC-02",
        "IFS-09-01", "IFS-09", "HAZ-26", "HAZ-3", "SRS-123", "banana",
    ):
        assert real.kind(anchor) == fake.kind(anchor), anchor
