"""Unit tests for the Thorne PR accessibility-check validator."""

import urllib.error

import pytest

from thorne_a11y_check import (
    HUMAN_ITEM_IDS,
    LanesError,
    determine_ui_surface,
    fetch_changed_files,
    fetch_ui_globs,
    glob_match,
    heuristic_ui_paths,
    is_web_path,
    lead_kind,
    main,
    parse_ui_globs,
    required_item_ids,
    section_bodies,
    sole_item_id,
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
    """Build a PR body in the *real template shape*.

    The ``## Accessibility`` section is wrapped in a ``<details>`` block, sits
    below a device-lane ``<details>`` block, and carries the HTML comment the
    template places between the lead boxes and the items — so the parser is
    exercised against the markup it actually receives, not a stripped-down form.

    ``lead`` is a subset of {"changes", "na"} for which lead boxes are ticked.
    ``present_ids`` renders those item checkboxes; ``checked_ids`` (a subset)
    are the ones ticked.
    """
    if not include_section:
        return (
            "## Summary\n\nA change.\n\n"
            "<details>\n<summary>Device-lane details</summary>\n\n"
            "## Thorne Scope\n\n- [x] Non-device function\n\n</details>\n"
        )
    item_lines = []
    for item_id in present_ids:
        mark = "x" if item_id in checked_ids else " "
        item_lines.append(f"- [{mark}] {_ITEM_TEXT[item_id]}")
    return (
        "## Summary\n"
        "\n"
        "A change.\n"
        "\n"
        "<details>\n"
        "<summary><b>Device-lane details</b></summary>\n"
        "\n"
        "## Thorne Scope\n"
        "\n"
        "<!-- classify -->\n"
        "\n"
        "- [x] Non-device function\n"
        "\n"
        "</details>\n"
        "\n"
        "<details>\n"
        "<summary><b>Accessibility</b> — fill in only for UI changes</summary>\n"
        "\n"
        "## Accessibility\n"
        "\n"
        f"- [{'x' if 'changes' in lead else ' '}] {LEAD_UI}\n"
        f"- [{'x' if 'na' in lead else ' '}] {LEAD_NA}\n"
        "\n"
        "<!-- If UI changed, confirm each item for the surfaces this PR touches: -->\n"
        "\n"
        + "\n".join(item_lines)
        + "\n"
        "\n"
        "</details>\n"
    )


# --- validate_accessibility: happy paths ------------------------------------


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


def test_real_template_shape_is_parsed():
    # The body carries a <details> wrapper, a device-lane block, and an HTML
    # comment between the leads and items — the parser must find the section
    # anyway (regression against a stripped-down test fixture).
    body = make_body(lead=("changes",))
    assert "<details>" in body and "<!--" in body
    assert validate_accessibility(body) == []


def test_crlf_body_passes():
    # GitHub returns CRLF bodies; parsing must be newline-agnostic.
    body = make_body(lead=("changes",)).replace("\n", "\r\n")
    assert validate_accessibility(body) == []


# --- validate_accessibility: structural errors ------------------------------


def test_empty_body_is_flagged():
    for body in ("", "   \n\t ", None):
        errs = validate_accessibility(body)
        assert len(errs) == 1 and "empty" in errs[0]


def test_missing_section_is_flagged():
    errs = validate_accessibility(make_body(include_section=False))
    assert any("Missing required section: ## Accessibility" in e for e in errs)


def test_missing_lead_ui_checkbox_is_flagged():
    body = make_body(lead=("na",), present_ids=(), checked_ids=())
    body = body.replace(f"- [ ] {LEAD_UI}\n", "")
    errs = validate_accessibility(body)
    assert any(
        "missing the lead checkbox 'This PR changes user-facing UI'" in e for e in errs
    )


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


# --- ID-keyed matching: the "cannot silently disarm" property ---------------


def test_reworded_item_text_still_matches_by_id():
    # A reword of the human text must not disarm the gate — matching is by ID.
    body = make_body(lead=("changes",))
    body = body.replace(
        "Every screen reads coherently under the screen reader.",
        "Totally different wording that still cites the check.",
    )
    assert validate_accessibility(body) == []


def test_changed_item_id_breaks_the_match():
    # The flip side of the property above: change the ID and the item no longer
    # counts, so the gate reports it missing (it cannot be silently renamed away).
    body = make_body(lead=("changes",)).replace("SR-01", "SR-99")
    errs = validate_accessibility(body)
    assert any("missing checklist item(s): SR-01" in e for e in errs)


# --- confirmed bypasses from review: findings 1, 2, 3 -----------------------


def test_appended_bullet_cannot_stand_in_for_na_lead():
    # Finding 1: leaving both leads unticked and appending an ordinary bullet
    # containing the words "no user-facing UI change" must NOT satisfy the gate.
    body = make_body(lead=())
    body = body.replace(
        "</details>\n",
        "- [x] Confirmed no user-facing UI change in this refactor\n</details>\n",
        1,
    )
    errs = validate_accessibility(body)
    assert any("Tick exactly one Accessibility lead box" in e for e in errs)


def test_bare_na_note_cannot_stand_in_for_na_lead():
    # Blocker 2: with both leads unticked, a plausible appended bullet that
    # starts with "N/A" but omits the template phrase must NOT satisfy the gate.
    body = make_body(lead=())
    body = body.replace(
        "</details>\n",
        "- [x] N/A for the design-token rename\n</details>\n",
        1,
    )
    errs = validate_accessibility(body)
    assert any("Tick exactly one Accessibility lead box" in e for e in errs)


def test_fenced_checkboxes_do_not_confirm():
    # Blocker 1: an all-ticked block pasted inside a ``` fence renders as inert
    # code on GitHub, so it must not confirm the checklist.
    body = make_body(lead=("changes",), present_ids=(), checked_ids=())
    forged = "```\n- [x] " + LEAD_UI + "\n"
    for item_id in HUMAN_ITEM_IDS:
        forged += "- [x] " + _ITEM_TEXT[item_id] + "\n"
    forged += "```\n"
    body = body.replace("</details>\n", forged + "</details>\n", 1)
    errs = validate_accessibility(body)
    assert any("missing checklist item(s)" in e for e in errs)


def test_indented_code_checkboxes_do_not_confirm():
    # Blocker 1: a >= 4-space-indented task list is a code block, not a checklist.
    body = make_body(lead=("changes",), present_ids=(), checked_ids=())
    indented = "".join(
        "    - [x] " + _ITEM_TEXT[item_id] + "\n" for item_id in HUMAN_ITEM_IDS
    )
    body = body.replace("</details>\n", indented + "</details>\n", 1)
    errs = validate_accessibility(body)
    assert any("missing checklist item(s)" in e for e in errs)


def test_single_line_listing_all_ids_confirms_none():
    # Finding 1 (aggregated): one line citing every ID must confirm none of them
    # — each item has to be its own distinct ticked line.
    body = make_body(lead=("changes",), present_ids=(), checked_ids=())
    aggregated = "- [x] Reviewed " + ", ".join(HUMAN_ITEM_IDS) + " with the a11y skill"
    body = body.replace("</details>\n", aggregated + "\n</details>\n", 1)
    errs = validate_accessibility(body)
    assert any("missing checklist item(s)" in e for e in errs)


def test_web_annotated_item_is_not_read_as_na_lead():
    # Finding 2: a correctly filled web PR whose TYPE-03 line is annotated with
    # "N/A … on web" must NOT trip the both-leads error — the line carries an ID,
    # so it is an item, never a lead.
    body = make_body(lead=("changes",))
    body = body.replace(
        "**TYPE-03** *(web)* — Content reflows at 320 CSS px / 400% zoom.",
        "**TYPE-03** *(web)* — N/A — no user-facing UI change on web; Android-only.",
    )
    # With every item ticked (including TYPE-03), a web PR passes cleanly.
    assert validate_accessibility(body, HUMAN_ITEM_IDS) == []


def test_duplicate_accessibility_section_is_flagged():
    # Finding 3: a second ## Accessibility heading (e.g. pasted feedback) is
    # ambiguous and must error rather than silently last-wins.
    body = make_body(lead=("changes",))
    body += "\n## Accessibility\n\n- [x] " + LEAD_NA + "\n"
    errs = validate_accessibility(body)
    assert any("more than one '## Accessibility' section" in e for e in errs)


def test_forged_section_inside_code_fence_is_ignored():
    # Finding 3: a forged all-ticked block inside a ``` fence is inert markup —
    # it must not override the real (N/A) declaration, nor count as a duplicate.
    body = make_body(lead=("na",), checked_ids=(), present_ids=HUMAN_ITEM_IDS)
    forged = (
        "\n```\n## Accessibility\n\n- [x] "
        + LEAD_UI
        + "\n- [x] "
        + LEAD_NA
        + "\n```\n"
    )
    assert validate_accessibility(body + forged) == []


def test_reviewer_feedback_after_details_does_not_cause_false_failure():
    # Finding 3: a complete declaration plus reviewer feedback pasted *after*
    # </details> (quoting the blank checklist) must still pass — the section is
    # bounded at the closing tag.
    body = make_body(lead=("changes",))
    pasted = (
        "\nReviewer: please double-check the blank checklist below:\n\n"
        "- [ ] " + LEAD_UI + "\n- [ ] " + LEAD_NA + "\n"
    )
    assert validate_accessibility(body + pasted) == []


def test_commented_out_checkbox_does_not_confirm():
    # A ticked checkbox hidden inside an HTML comment must not count.
    body = make_body(lead=("changes",), present_ids=(), checked_ids=())
    commented = "<!--\n- [x] " + _ITEM_TEXT["SR-01"] + "\n-->"
    body = body.replace("</details>\n", commented + "\n</details>\n", 1)
    errs = validate_accessibility(body)
    assert any("missing checklist item(s): SR-01" in e for e in errs)


# --- GFM bullet variants ----------------------------------------------------


def test_star_and_plus_bullets_are_task_lists():
    body = make_body(lead=("changes",)).replace("- [", "* [")
    assert validate_accessibility(body) == []
    body = make_body(lead=("changes",)).replace("- [", "+ [")
    assert validate_accessibility(body) == []


# --- TYPE-03 web scoping ----------------------------------------------------


def test_required_item_ids_scopes_web_only_item():
    assert "TYPE-03" in required_item_ids(is_web=True)
    assert "TYPE-03" not in required_item_ids(is_web=False)
    assert set(required_item_ids(True)) - {"TYPE-03"} == set(required_item_ids(False))


def test_native_pr_may_leave_type03_unticked():
    checked = tuple(i for i in HUMAN_ITEM_IDS if i != "TYPE-03")
    body = make_body(lead=("changes",), checked_ids=checked)
    # Web scope would flag it; native scope must not.
    assert any("TYPE-03" in e for e in validate_accessibility(body, HUMAN_ITEM_IDS))
    assert validate_accessibility(body, required_item_ids(is_web=False)) == []


def test_type03_still_required_present_on_native():
    # Even when its tick is optional, TYPE-03 must be *rendered* (template integrity).
    present = tuple(i for i in HUMAN_ITEM_IDS if i != "TYPE-03")
    body = make_body(lead=("changes",), present_ids=present, checked_ids=present)
    errs = validate_accessibility(body, required_item_ids(is_web=False))
    assert any("missing checklist item(s): TYPE-03" in e for e in errs)


# --- lead_kind / sole_item_id (unit) ----------------------------------------


def test_lead_kind_classifies_leads_and_items():
    assert lead_kind("This PR changes user-facing UI") == "changes"
    assert lead_kind("N/A — no user-facing UI change") == "na"
    # An item line (carries an ID) is never a lead.
    assert lead_kind("**TYPE-03** *(web)* — N/A — no user-facing UI change") is None
    # A sentence merely containing the phrase is not a lead.
    assert lead_kind("Confirmed no user-facing UI change in this refactor") is None
    # A bare "N/A" note without the template phrase is not the N/A lead.
    assert lead_kind("N/A for the design-token rename") is None


def test_sole_item_id_requires_exactly_one():
    assert sole_item_id("**SR-01** — text") == "SR-01"
    assert sole_item_id("Reviewed SR-01, SR-02 together") is None
    assert sole_item_id("no id here") is None


def test_section_bodies_returns_all_duplicates():
    md = "## A\n\nfirst\n\n## A\n\nsecond\n"
    assert section_bodies(md, "A") == ["first", "second"]


# --- parse_ui_globs ---------------------------------------------------------


def test_parse_ui_globs_block_list():
    yaml = (
        "ui:\n"
        '  - "app/src/main/kotlin/**/ui/**"\n'
        "  - app/src/main/res/**  # resources\n"
    )
    globs, saw_key, warnings = parse_ui_globs(yaml)
    assert globs == ["app/src/main/kotlin/**/ui/**", "app/src/main/res/**"]
    assert saw_key is True and warnings == []


def test_parse_ui_globs_absent_means_no_key():
    for yaml in ("non_device:\n  - docs/**\n", "", None):
        globs, saw_key, warnings = parse_ui_globs(yaml)
        assert globs == [] and saw_key is False and warnings == []


def test_parse_ui_globs_explicit_empty_list_is_authoritative():
    # `ui: []` declares no UI surface (saw_key True); a stray item must not leak.
    globs, saw_key, _ = parse_ui_globs("ui: []\n  - app/src/main/ui/**\n")
    assert globs == [] and saw_key is True


def test_parse_ui_globs_stops_at_next_top_level_key():
    yaml = "ui:\n  - src/ui/**\nnon_device:\n  - docs/**\n"
    globs, saw_key, _ = parse_ui_globs(yaml)
    assert globs == ["src/ui/**"] and saw_key is True


@pytest.mark.parametrize(
    "yaml",
    ['ui: ["src/lib/**"]\n', 'ui: "src/lib/**"\n', "ui: src/lib/**\n"],
)
def test_parse_ui_globs_rejects_unsupported_inline_shapes(yaml):
    # Finding 5: an inline shape the parser cannot honor must fail loud, not
    # silently read no UI surface (fail-open).
    with pytest.raises(LanesError):
        parse_ui_globs(yaml)


def test_parse_ui_globs_warns_on_miscased_key():
    globs, saw_key, warnings = parse_ui_globs("UI:\n  - src/ui/**\n")
    assert globs == [] and saw_key is False
    assert warnings and "lowercase 'ui:'" in warnings[0]


def test_parse_ui_globs_warns_on_nested_key():
    # Suggestion 2: an indented `ui:` (e.g. nested under a `lanes:` parent) is
    # not the top-level key the parser reads; it must warn, not silently pass.
    globs, saw_key, warnings = parse_ui_globs('lanes:\n  ui:\n    - "src/**"\n')
    assert globs == [] and saw_key is False
    assert warnings and "top-level" in warnings[0]


def test_parse_ui_globs_top_level_block_list_items_are_not_nested_keys():
    # A well-formed top-level block list must not trip the nested-key warning.
    globs, saw_key, warnings = parse_ui_globs('ui:\n  - "src/ui/**"\n')
    assert globs == ["src/ui/**"] and saw_key is True and warnings == []


def test_parse_ui_globs_preserves_hash_in_glob():
    # A '#' with no leading space is part of the glob, not a comment.
    globs, _, _ = parse_ui_globs('ui:\n  - "src/c#/**"\n')
    assert globs == ["src/c#/**"]


# --- glob_match: segment semantics (finding 4) ------------------------------


def test_glob_star_stays_within_segment():
    assert glob_match("apps/patient/src/routes/x.svelte", "apps/*/src/**")
    assert not glob_match("apps/patient/nested/src/x", "apps/*/src/**")


def test_globstar_slash_matches_whole_segments_only():
    # Finding 4: **/ must match zero or more *complete* segments, so a literal
    # directory name after it cannot match a suffix of another directory.
    assert not glob_match("app/notui/Home.kt", "app/**/ui/**")
    assert not glob_match("src/xui/a.ts", "src/**/ui/**")
    assert glob_match("app/ui/Home.kt", "app/**/ui/**")
    assert glob_match("app/feature/x/ui/Home.kt", "app/**/ui/**")


def test_ui_paths_matches_only_ui_globs():
    changed = [
        "app/src/main/kotlin/com/eiro/thorne/patient/ui/Home.kt",
        "app/src/main/kotlin/com/eiro/thorne/patient/net/Api.kt",
        "README.md",
    ]
    globs = ["app/src/main/kotlin/com/eiro/thorne/patient/ui/**"]
    assert ui_paths(changed, globs) == [
        "app/src/main/kotlin/com/eiro/thorne/patient/ui/Home.kt"
    ]


# --- heuristic + web detection ----------------------------------------------


def test_heuristic_matches_web_and_native_paths():
    changed = [
        "web/src/routes/+page.svelte",
        "app/src/main/kotlin/x/ui/Home.kt",
        "app/src/main/res/values/strings.xml",
        "server/api/handler.py",
        "README.md",
    ]
    hits = heuristic_ui_paths(changed)
    assert "web/src/routes/+page.svelte" in hits
    assert "app/src/main/kotlin/x/ui/Home.kt" in hits
    assert "app/src/main/res/values/strings.xml" in hits
    assert "server/api/handler.py" not in hits
    assert "README.md" not in hits


def test_is_web_path():
    assert is_web_path("web/src/routes/+page.svelte")
    assert is_web_path("packages/patient/Button.svelte")
    assert not is_web_path("app/src/main/kotlin/x/ui/Home.kt")
    assert not is_web_path("app/src/main/res/values/strings.xml")


def test_is_web_path_recognizes_framework_and_markup_files():
    # Suggestion 1: React/Vue/Astro/plain-HTML files are web, so TYPE-03 is not
    # silently optional on a repo whose UI surface is those file types.
    assert is_web_path("apps/web/app/page.tsx")
    assert is_web_path("src/App.jsx")
    assert is_web_path("src/components/Card.vue")
    assert is_web_path("src/pages/index.astro")
    assert is_web_path("public/index.html")


# --- determine_ui_surface ---------------------------------------------------


def _ctx(monkeypatch, repo="eiro-inc/x", pr="1", base="main"):
    monkeypatch.setenv("REPO", repo)
    monkeypatch.setenv("PR_NUMBER", pr)
    monkeypatch.setenv("BASE_REF", base)


def _files(monkeypatch, files, truncated=False):
    monkeypatch.setattr(
        "thorne_a11y_check.fetch_changed_files",
        lambda repo, pr: (list(files), truncated),
    )


def _lanes(monkeypatch, globs, saw_key=True, warnings=()):
    monkeypatch.setattr(
        "thorne_a11y_check.fetch_ui_globs",
        lambda repo, ref: (list(globs), saw_key, list(warnings)),
    )


def test_determine_ui_surface_authoritative_ui_block(monkeypatch):
    _ctx(monkeypatch)
    _files(monkeypatch, ["app/x/ui/Home.kt", "README.md"])
    _lanes(monkeypatch, ["**/ui/**"], saw_key=True)
    is_ui, is_web, triggering, _ = determine_ui_surface()
    assert is_ui is True and is_web is False
    assert triggering == ["app/x/ui/Home.kt"]


def test_determine_ui_surface_web_sets_is_web(monkeypatch):
    _ctx(monkeypatch)
    _files(monkeypatch, ["web/src/routes/+page.svelte"])
    _lanes(monkeypatch, ["**/*.svelte"], saw_key=True)
    is_ui, is_web, triggering, _ = determine_ui_surface()
    assert is_ui is True and is_web is True


def test_determine_ui_surface_non_ui_lane(monkeypatch):
    _ctx(monkeypatch)
    _files(monkeypatch, ["docs/x.md"])
    _lanes(monkeypatch, ["**/ui/**"], saw_key=True)
    is_ui, is_web, triggering, _ = determine_ui_surface()
    assert is_ui is False and is_web is False and triggering == []


def test_determine_ui_surface_falls_back_to_heuristic_without_ui_block(monkeypatch):
    # Finding 5 / Phase-1: no ui: block -> file-path heuristic (per the skill).
    _ctx(monkeypatch)
    _files(monkeypatch, ["app/src/main/res/values/strings.xml", "README.md"])
    _lanes(monkeypatch, [], saw_key=False)
    is_ui, is_web, triggering, messages = determine_ui_surface()
    assert is_ui is True
    assert triggering == ["app/src/main/res/values/strings.xml"]
    assert any("Phase-1 file-path heuristic" in text for _lvl, text in messages)


def test_determine_ui_surface_heuristic_no_match_is_non_ui(monkeypatch):
    _ctx(monkeypatch)
    _files(monkeypatch, ["server/api/handler.py", "README.md"])
    _lanes(monkeypatch, [], saw_key=False)
    is_ui, is_web, triggering, _ = determine_ui_surface()
    assert is_ui is False and triggering == []


def test_determine_ui_surface_fails_safe_on_empty_base_ref(monkeypatch):
    # Finding 6: an empty BASE_REF is indeterminable and must fail safe.
    _ctx(monkeypatch, base="")
    is_ui, is_web, triggering, messages = determine_ui_surface()
    assert is_ui is True and is_web is True and triggering is None
    assert any("fail-safe" in text for _lvl, text in messages)


def test_determine_ui_surface_fails_safe_without_pr_context(monkeypatch):
    for var in ("REPO", "PR_NUMBER", "BASE_REF"):
        monkeypatch.delenv(var, raising=False)
    is_ui, is_web, triggering, messages = determine_ui_surface()
    assert is_ui is True and is_web is True and triggering is None
    assert any("fail-safe" in text for _lvl, text in messages)


def test_determine_ui_surface_fails_safe_on_truncated_file_list(monkeypatch):
    _ctx(monkeypatch)
    _files(monkeypatch, ["app/x/ui/Home.kt"], truncated=True)
    is_ui, is_web, triggering, messages = determine_ui_surface()
    assert is_ui is True and is_web is True and triggering is None
    assert any("3000-file" in text for _lvl, text in messages)


def test_determine_ui_surface_fails_safe_on_unparseable_lanes(monkeypatch):
    _ctx(monkeypatch)
    _files(monkeypatch, ["app/x/ui/Home.kt"])

    def boom(repo, ref):
        raise LanesError("bad shape")

    monkeypatch.setattr("thorne_a11y_check.fetch_ui_globs", boom)
    is_ui, is_web, triggering, messages = determine_ui_surface()
    assert is_ui is True and is_web is True and triggering is None
    assert any("Unparseable" in text for _lvl, text in messages)


def test_determine_ui_surface_fails_safe_on_api_error(monkeypatch):
    _ctx(monkeypatch)

    def boom(repo, pr):
        raise RuntimeError("boom")

    monkeypatch.setattr("thorne_a11y_check.fetch_changed_files", boom)
    is_ui, is_web, triggering, _ = determine_ui_surface()
    assert is_ui is True and is_web is True and triggering is None


def test_determine_ui_surface_surfaces_lanes_warning(monkeypatch):
    _ctx(monkeypatch)
    _files(monkeypatch, ["server/api/handler.py"])
    _lanes(monkeypatch, [], saw_key=False, warnings=["mis-cased UI key"])
    _is_ui, _is_web, _triggering, messages = determine_ui_surface()
    assert any(lvl == "warning" and "mis-cased" in text for lvl, text in messages)


# --- fetch helpers ----------------------------------------------------------


def test_fetch_changed_files_includes_rename_old_path(monkeypatch):
    batch = [
        {"filename": "app/ui/New.kt", "previous_filename": "app/ui/Old.kt"},
        {"filename": "README.md"},
    ]
    monkeypatch.setattr("thorne_a11y_check._gh_get", lambda path: batch)
    files, truncated = fetch_changed_files("eiro-inc/x", "1")
    assert "app/ui/New.kt" in files and "app/ui/Old.kt" in files
    assert truncated is False


def test_fetch_changed_files_flags_truncation(monkeypatch):
    # 31 pages of 100 (> 3000-file cap) reports truncated without looping forever.
    full = [{"filename": f"f{i}.kt"} for i in range(100)]

    def paged(path):
        return full

    monkeypatch.setattr("thorne_a11y_check._gh_get", paged)
    _files, truncated = fetch_changed_files("eiro-inc/x", "1")
    assert truncated is True


def test_fetch_ui_globs_returns_no_key_when_lanes_file_missing(monkeypatch):
    def raise_404(path):
        raise urllib.error.HTTPError(path, 404, "Not Found", {}, None)

    monkeypatch.setattr("thorne_a11y_check._gh_get", raise_404)
    assert fetch_ui_globs("eiro-inc/x", "main") == ([], False, [])


def test_fetch_ui_globs_reraises_non_404(monkeypatch):
    def raise_500(path):
        raise urllib.error.HTTPError(path, 500, "Server Error", {}, None)

    monkeypatch.setattr("thorne_a11y_check._gh_get", raise_500)
    with pytest.raises(urllib.error.HTTPError):
        fetch_ui_globs("eiro-inc/x", "main")


# --- main -------------------------------------------------------------------


def _stub_surface(monkeypatch, is_ui, is_web=True, triggering=("app/ui/Home.kt",)):
    monkeypatch.setattr(
        "thorne_a11y_check.determine_ui_surface",
        lambda: (is_ui, is_web, list(triggering) if triggering else [], []),
    )


def test_main_passes_on_complete_ui_body(monkeypatch, capsys):
    monkeypatch.setenv("PR_BODY", make_body(lead=("changes",)))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    _stub_surface(monkeypatch, True, is_web=True)
    main()
    assert "complete" in capsys.readouterr().out


def test_main_fails_on_incomplete_ui_body(monkeypatch, capsys):
    monkeypatch.setenv("PR_BODY", make_body(lead=()))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    _stub_surface(monkeypatch, True)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "::error::" in capsys.readouterr().out


def test_main_native_lane_ignores_unticked_type03(monkeypatch, capsys):
    # A native UI PR whose only unticked item is TYPE-03 must pass.
    checked = tuple(i for i in HUMAN_ITEM_IDS if i != "TYPE-03")
    monkeypatch.setenv("PR_BODY", make_body(lead=("changes",), checked_ids=checked))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    _stub_surface(monkeypatch, True, is_web=False)
    main()
    assert "complete" in capsys.readouterr().out


def test_main_passes_on_non_ui_lane_regardless_of_body(monkeypatch, capsys):
    monkeypatch.setenv("PR_BODY", "## Summary\n\nBackend only.\n")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    _stub_surface(monkeypatch, False, is_web=False, triggering=())
    main()
    assert "complete" in capsys.readouterr().out


def test_main_writes_step_summary(monkeypatch, tmp_path):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("PR_BODY", make_body(lead=("changes",)))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    _stub_surface(monkeypatch, True, is_web=True)
    main()
    text = summary.read_text()
    assert "Thorne A11y Check" in text and "accessibility required" in text
