"""Unit tests for the Thorne PR accessibility-check validator."""

import urllib.error

import pytest

from thorne_a11y_check import (
    HUMAN_ITEM_IDS,
    determine_ui_surface,
    fetch_changed_files,
    fetch_ui_globs,
    glob_match,
    main,
    parse_ui_globs,
    ui_paths,
    validate_accessibility,
)

LEAD_UI = "This PR changes user-facing UI"
LEAD_NA = "N/A — no user-facing UI change"

# The item text mirrors the template (an em-dash and the stable ID); the gate
# keys on the ID, so the surrounding wording here is illustrative only.
_ITEM_TEXT = {
    "SR-01": "**SR-01** — Every screen reads coherently under the screen reader.",
    "SR-02": "**SR-02** — Reading / traversal order matches visual order.",
    "CD-03": "**CD-03** — Content descriptions convey information, not file names.",
    "FORM-01": "**FORM-01** — Form fields have meaningful, persistent labels.",
    "TYPE-02": "**TYPE-02** — Layout stays usable at the largest font setting.",
    "TYPE-03": "**TYPE-03** *(web)* — Content reflows at 320 CSS px / 400% zoom.",
    "COLOR-03": "**COLOR-03** — Color is never the only way info is conveyed.",
    "FOCUS-01": "**FOCUS-01** — All interactive elements are keyboard-operable.",
}


def make_body(
    lead=("changes",),
    checked_ids=HUMAN_ITEM_IDS,
    present_ids=HUMAN_ITEM_IDS,
    include_section=True,
):
    """Build a PR body with a ## Accessibility section.

    ``lead`` is a subset of {"changes", "na"} for which lead boxes are ticked.
    ``present_ids`` renders those item checkboxes; ``checked_ids`` (a subset)
    are the ones ticked.
    """
    if not include_section:
        return "## Summary\n\nA change.\n"
    lines = [
        "## Summary",
        "",
        "A change.",
        "",
        "## Accessibility",
        "",
        f"- [{'x' if 'changes' in lead else ' '}] {LEAD_UI}",
        f"- [{'x' if 'na' in lead else ' '}] {LEAD_NA}",
        "",
    ]
    for item_id in present_ids:
        mark = "x" if item_id in checked_ids else " "
        lines.append(f"- [{mark}] {_ITEM_TEXT[item_id]}")
    return "\n".join(lines) + "\n"


# --- validate_accessibility -------------------------------------------------


def test_valid_changes_ui_body_passes():
    assert validate_accessibility(make_body(lead=("changes",))) == []


def test_valid_na_body_passes():
    # N/A satisfies the gate even though the UI lane was triggered: a touched UI
    # file may be a non-user-facing change, and the reviewer owns that call.
    body = make_body(lead=("na",), checked_ids=(), present_ids=HUMAN_ITEM_IDS)
    assert validate_accessibility(body) == []


def test_na_passes_even_without_item_checkboxes():
    body = make_body(lead=("na",), present_ids=(), checked_ids=())
    assert validate_accessibility(body) == []


def test_empty_body_is_flagged():
    for body in ("", "   \n\t ", None):
        errs = validate_accessibility(body)
        assert len(errs) == 1 and "empty" in errs[0]


def test_missing_section_is_flagged():
    errs = validate_accessibility(make_body(include_section=False))
    assert any("Missing required section: ## Accessibility" in e for e in errs)


def test_missing_lead_ui_checkbox_is_flagged():
    body = make_body(lead=("na",), present_ids=(), checked_ids=())
    # Remove the "changes user-facing UI" lead line entirely.
    body = body.replace(f"- [ ] {LEAD_UI}\n", "")
    errs = validate_accessibility(body)
    assert any("missing the lead checkbox 'This PR changes user-facing UI'" in e for e in errs)


def test_missing_lead_na_checkbox_is_flagged():
    body = make_body(lead=("changes",))
    body = body.replace(f"- [ ] {LEAD_NA}\n", "")
    errs = validate_accessibility(body)
    assert any("N/A — no user-facing UI change" in e for e in errs)


def test_neither_lead_ticked_is_flagged():
    errs = validate_accessibility(make_body(lead=()))
    assert any("Tick exactly one Accessibility lead box" in e for e in errs)


def test_both_leads_ticked_is_flagged():
    errs = validate_accessibility(make_body(lead=("changes", "na")))
    assert any("Do not tick both Accessibility lead boxes" in e for e in errs)


def test_changes_ui_missing_item_is_flagged():
    present = tuple(i for i in HUMAN_ITEM_IDS if i != "FORM-01")
    body = make_body(lead=("changes",), present_ids=present, checked_ids=present)
    errs = validate_accessibility(body)
    assert any("missing checklist item(s): FORM-01" in e for e in errs)


def test_changes_ui_unticked_item_is_flagged():
    checked = tuple(i for i in HUMAN_ITEM_IDS if i != "COLOR-03")
    body = make_body(lead=("changes",), checked_ids=checked)
    errs = validate_accessibility(body)
    assert any("unticked: COLOR-03" in e for e in errs)


def test_reworded_item_text_still_matches_by_id():
    # A reword of the human text must not disarm the gate — matching is by ID.
    body = make_body(lead=("changes",))
    body = body.replace(
        "Every screen reads coherently under the screen reader.",
        "Totally different wording that still cites the check.",
    )
    assert validate_accessibility(body) == []


# --- parse_ui_globs ---------------------------------------------------------


def test_parse_ui_globs_block_list():
    yaml = (
        "ui:\n"
        '  - "app/src/main/kotlin/**/ui/**"\n'
        "  - app/src/main/res/**  # resources\n"
    )
    assert parse_ui_globs(yaml) == [
        "app/src/main/kotlin/**/ui/**",
        "app/src/main/res/**",
    ]


def test_parse_ui_globs_absent_means_no_ui_surface():
    assert parse_ui_globs("non_device:\n  - docs/**\n") == []
    assert parse_ui_globs("") == []
    assert parse_ui_globs(None) == []


def test_parse_ui_globs_explicit_empty_list_does_not_open_block():
    # `ui: []` declares no UI surface; a stray following item must not leak in.
    yaml = "ui: []\n  - app/src/main/ui/**\n"
    assert parse_ui_globs(yaml) == []


def test_parse_ui_globs_stops_at_next_top_level_key():
    # ui: and non_device: coexist in one lanes file (two axes); each parser
    # reads only its own key and stops at the next top-level key.
    yaml = (
        "ui:\n"
        "  - src/ui/**\n"
        "non_device:\n"
        "  - docs/**\n"
    )
    assert parse_ui_globs(yaml) == ["src/ui/**"]


# --- ui_paths / glob_match --------------------------------------------------


def test_ui_paths_matches_only_ui_globs():
    changed = [
        "app/src/main/kotlin/com/eiro/thorne/patient/ui/Home.kt",
        "app/src/main/kotlin/com/eiro/thorne/patient/net/Api.kt",
        "app/src/main/res/values/strings.xml",
        "README.md",
    ]
    globs = [
        "app/src/main/kotlin/com/eiro/thorne/patient/ui/**",
        "app/src/main/res/**",
    ]
    assert ui_paths(changed, globs) == [
        "app/src/main/kotlin/com/eiro/thorne/patient/ui/Home.kt",
        "app/src/main/res/values/strings.xml",
    ]


def test_ui_paths_empty_when_no_globs():
    assert ui_paths(["src/ui/Home.kt"], []) == []


def test_glob_star_stays_within_segment():
    assert glob_match("apps/patient/src/routes/x.svelte", "apps/*/src/**")
    assert not glob_match("apps/patient/nested/src/x", "apps/*/src/**")


# --- determine_ui_surface ---------------------------------------------------


def test_determine_ui_surface_ui_lane(monkeypatch):
    monkeypatch.setenv("REPO", "eiro-inc/thorne-patient-android")
    monkeypatch.setenv("PR_NUMBER", "1")
    monkeypatch.setenv("BASE_REF", "main")
    monkeypatch.setattr(
        "thorne_a11y_check.fetch_changed_files",
        lambda repo, pr: ["app/src/main/kotlin/x/ui/Home.kt", "README.md"],
    )
    monkeypatch.setattr(
        "thorne_a11y_check.fetch_ui_globs", lambda repo, ref: ["**/ui/**"]
    )
    is_ui, triggering, note = determine_ui_surface()
    assert is_ui is True
    assert triggering == ["app/src/main/kotlin/x/ui/Home.kt"]
    assert note == ""


def test_determine_ui_surface_non_ui_lane(monkeypatch):
    monkeypatch.setenv("REPO", "eiro-inc/thorne-patient-android")
    monkeypatch.setenv("PR_NUMBER", "1")
    monkeypatch.setenv("BASE_REF", "main")
    monkeypatch.setattr(
        "thorne_a11y_check.fetch_changed_files", lambda repo, pr: ["docs/x.md"]
    )
    monkeypatch.setattr(
        "thorne_a11y_check.fetch_ui_globs", lambda repo, ref: ["**/ui/**"]
    )
    is_ui, triggering, note = determine_ui_surface()
    assert is_ui is False
    assert triggering == []


def test_determine_ui_surface_fails_safe_when_no_changed_files(monkeypatch):
    monkeypatch.setenv("REPO", "eiro-inc/thorne-patient-android")
    monkeypatch.setenv("PR_NUMBER", "1")
    monkeypatch.setenv("BASE_REF", "main")
    monkeypatch.setattr("thorne_a11y_check.fetch_changed_files", lambda repo, pr: [])
    monkeypatch.setattr("thorne_a11y_check.fetch_ui_globs", lambda repo, ref: ["**/ui/**"])
    is_ui, triggering, note = determine_ui_surface()
    assert is_ui is True and triggering is None and "fail-safe" in note


def test_determine_ui_surface_fails_safe_without_pr_context(monkeypatch):
    for var in ("REPO", "PR_NUMBER", "BASE_REF"):
        monkeypatch.delenv(var, raising=False)
    is_ui, triggering, note = determine_ui_surface()
    assert is_ui is True and triggering is None and "fail-safe" in note


def test_determine_ui_surface_fails_safe_on_api_error(monkeypatch):
    monkeypatch.setenv("REPO", "eiro-inc/thorne-patient-android")
    monkeypatch.setenv("PR_NUMBER", "1")
    monkeypatch.setenv("BASE_REF", "main")

    def boom(repo, pr):
        raise RuntimeError("boom")

    monkeypatch.setattr("thorne_a11y_check.fetch_changed_files", boom)
    is_ui, triggering, note = determine_ui_surface()
    assert is_ui is True and triggering is None and "fail-safe" in note


# --- fetch helpers ----------------------------------------------------------


def test_fetch_changed_files_includes_rename_old_path(monkeypatch):
    batch = [
        {"filename": "app/ui/New.kt", "previous_filename": "app/ui/Old.kt"},
        {"filename": "README.md"},
    ]
    monkeypatch.setattr("thorne_a11y_check._gh_get", lambda path: batch)
    files = fetch_changed_files("eiro-inc/x", "1")
    assert "app/ui/New.kt" in files and "app/ui/Old.kt" in files


def test_fetch_ui_globs_returns_empty_when_lanes_file_missing(monkeypatch):
    def raise_404(path):
        raise urllib.error.HTTPError(path, 404, "Not Found", {}, None)

    monkeypatch.setattr("thorne_a11y_check._gh_get", raise_404)
    assert fetch_ui_globs("eiro-inc/x", "main") == []


def test_fetch_ui_globs_reraises_non_404(monkeypatch):
    def raise_500(path):
        raise urllib.error.HTTPError(path, 500, "Server Error", {}, None)

    monkeypatch.setattr("thorne_a11y_check._gh_get", raise_500)
    with pytest.raises(urllib.error.HTTPError):
        fetch_ui_globs("eiro-inc/x", "main")


# --- main -------------------------------------------------------------------


def _stub_ui_lane(monkeypatch, is_ui, triggering=("app/ui/Home.kt",)):
    monkeypatch.setattr(
        "thorne_a11y_check.determine_ui_surface",
        lambda: (is_ui, list(triggering) if triggering else [], ""),
    )


def test_main_passes_on_complete_ui_body(monkeypatch, capsys):
    monkeypatch.setenv("PR_BODY", make_body(lead=("changes",)))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    _stub_ui_lane(monkeypatch, True)
    main()
    assert "complete" in capsys.readouterr().out


def test_main_fails_on_incomplete_ui_body(monkeypatch, capsys):
    monkeypatch.setenv("PR_BODY", make_body(lead=()))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    _stub_ui_lane(monkeypatch, True)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "::error::" in capsys.readouterr().out


def test_main_passes_on_non_ui_lane_regardless_of_body(monkeypatch, capsys):
    # A non-UI PR needs no Accessibility section at all.
    monkeypatch.setenv("PR_BODY", "## Summary\n\nBackend only.\n")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    _stub_ui_lane(monkeypatch, False, triggering=())
    main()
    assert "complete" in capsys.readouterr().out


def test_main_writes_step_summary(monkeypatch, tmp_path):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("PR_BODY", make_body(lead=("changes",)))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    _stub_ui_lane(monkeypatch, True)
    main()
    text = summary.read_text()
    assert "Thorne A11y Check" in text and "ui (accessibility required)" in text
