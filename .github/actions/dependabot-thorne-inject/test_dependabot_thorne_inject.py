"""Unit tests for the device-lane Dependabot template injector."""

import dependabot_thorne_inject as inj


# Captured once, before any monkeypatch of _load_boundary.
_REAL_BOUNDARY = inj._load_boundary()


class _StubBoundary:
    def __init__(self, lane):
        self._lane = lane

    def determine_lane(self):
        return (self._lane, [], "")

    def __getattr__(self, name):
        return getattr(_REAL_BOUNDARY, name)


def test_load_boundary_imports_sibling_module():
    # The action relies on running from the same .github checkout as the
    # boundary-check action, so it can import determine_lane directly.
    boundary = inj._load_boundary()
    assert callable(boundary.determine_lane)
    assert callable(boundary.validate)


def test_build_body_appends_marker_note_and_template():
    out = inj.build_body("Bumps foo from 1 to 2.", "<!--M-->", "NOTE", "## Summary\n\n…")
    assert out.startswith("Bumps foo from 1 to 2.")
    assert "<!--M-->" in out
    assert "NOTE" in out
    assert "## Summary" in out


def test_build_body_handles_empty_original():
    out = inj.build_body("", "<!--M-->", "NOTE", "## Summary")
    assert out.startswith("<!--M-->")


def test_main_noops_on_non_device(monkeypatch):
    calls = []
    monkeypatch.setattr(inj, "_load_boundary", lambda: _StubBoundary("non_device"))
    monkeypatch.setattr(inj, "gh", lambda *a: calls.append(a) or "")

    assert inj.main() == 0
    assert calls == []  # never touches the PR


def test_main_noops_when_marker_already_present(monkeypatch):
    calls = []

    def fake_gh(*a):
        calls.append(a)
        if a[:2] == ("pr", "view"):
            return "Bumps foo.\n\n<!-- thorne-boundary-block -->\n"
        return ""

    monkeypatch.setattr(inj, "_load_boundary", lambda: _StubBoundary("device"))
    monkeypatch.setattr(inj, "gh", fake_gh)
    monkeypatch.setenv("REPO", "eiro-inc/x")
    monkeypatch.setenv("PR_NUMBER", "1")

    assert inj.main() == 0
    assert not any(a[:2] == ("pr", "edit") for a in calls)  # no re-inject


def test_has_required_sections_detects_full_template():
    boundary = inj._load_boundary()
    full = "\n\n".join(f"## {section}\n\nx" for section in boundary.REQUIRED_SECTIONS)
    assert inj.has_required_sections(boundary, full)
    assert not inj.has_required_sections(boundary, "Bumps foo from 1 to 2.")


def test_main_noops_when_body_already_has_template(monkeypatch):
    # Body already carries every section but NO marker — must not re-append.
    boundary = inj._load_boundary()
    body = "\n\n".join(f"## {section}\n\nx" for section in boundary.REQUIRED_SECTIONS)
    calls = []

    def fake_gh(*a):
        calls.append(a)
        return body if a[:2] == ("pr", "view") else ""

    monkeypatch.setattr(inj, "_load_boundary", lambda: _StubBoundary("device"))
    monkeypatch.setattr(inj, "gh", fake_gh)
    monkeypatch.setenv("REPO", "eiro-inc/x")
    monkeypatch.setenv("PR_NUMBER", "1")

    assert inj.main() == 0
    assert not any(a[:2] == ("pr", "edit") for a in calls)


def test_main_injects_template_on_device_without_marker(monkeypatch):
    calls = []

    def fake_gh(*a):
        calls.append(a)
        if a[:2] == ("pr", "view"):
            return "Bumps foo from 1 to 2."  # raw Dependabot body, no marker
        return ""

    monkeypatch.setattr(inj, "_load_boundary", lambda: _StubBoundary("device"))
    monkeypatch.setattr(inj, "gh", fake_gh)
    monkeypatch.setenv("REPO", "eiro-inc/x")
    monkeypatch.setenv("PR_NUMBER", "1")

    assert inj.main() == 0
    edits = [a for a in calls if a[:2] == ("pr", "edit")]
    assert len(edits) == 1  # body was rewritten exactly once
