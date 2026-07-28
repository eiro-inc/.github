## Summary

<!-- What changed and why. This is all a non-device PR needs. -->

## Related Issue

<!-- Link the repository issue (e.g. Closes #123), or write N/A. -->

<!--
──────────────────────────────────────────────────────────────────────────
DEVICE-LANE SECTION ↓  — only required if this PR touches device code.

The `thorne-pr-boundary-check` decides the lane automatically from the files
you changed: everything is device unless carved out in `.github/thorne-lanes.yml`.
The lane selects lifecycle controls; it does not by itself classify the
product function. A non-device function can use this lane when it changes an
unsegregated device software item.

• Non-device PR? Leave the block below as-is (or delete it) and you're done.
• Device PR? The check fails until the block is filled in — and it lists the
  exact files that put you on the device lane.
──────────────────────────────────────────────────────────────────────────
-->

<details>
<summary><b>Device-lane details</b> — fill in only for device-code changes</summary>

## Thorne Scope

<!-- Classify the product purpose separately from the affected implementation.
     Example: a patient self-view implemented through an unsegregated device
     item selects Non-device function + Multiple-Function impact assessment,
     not Device function merely because the PR is on the device lane.
     Internal build, test, deployment, or lifecycle tooling is not a product
     function: select DHF/QMS artifact, trace its consuming use to CMP
     §§4.1/6/9, and use Safety Class N/A when no ARC item is affected. -->

- [ ] Device function
- [ ] Non-device function
- [ ] Multiple-Function impact assessment
- [ ] Pre-design scaffolding under CMP §7
- [ ] DHF/QMS artifact
- [ ] Not Thorne-related

## DHF Trace

<!-- Cite controlling anchors: CMP §7, DDS §5/§6/§7, UNS, SRS, SDD, HAZ, TRM, DR, etc. -->

## Affected Device Software Items

<!-- One line per device software item this PR changes, including a segregated
     lower-class functional item and every unsegregated shared item it changes:
       ARC-01 — Class B — cadence reducer
       ARC-04 — Class C — persistence / authoritative projection
     Product-function scope and affected-item class are separate axes. A
     Non-device function + Multiple-Function impact PR may therefore identify
     ARC-04 — Class C. If no device item is affected, explain why. -->

- N/A — no device software item affected

## Safety Class

<!-- Select every class named under Affected Device Software Items. These are
     software-item classes, not a classification of the product purpose. -->

- [ ] Class A
- [ ] Class B
- [ ] Class C
- [ ] N/A
- [ ] TBD / blocked until resolved

## Verification Tests

<!-- One line per verification test ADDED, CHANGED, or REMOVED in this PR,
     with its @verifies target(s). A verification test is one that confirms
     an SRS requirement (VVP-01 §6.8): it carries the @verifies tag and is
     CI-harvested into the TRM.
       test_offline_sync_no_loss — @verifies SRS-01-04
       removed test_old_sync — @verifies SRS-01-04; re-covered by test_offline_sync_no_loss
     Removing, renaming, or disabling a tagged test orphans a TRM row's
     evidence — always list it and say how the requirement stays covered.
     If the PR also touches tests that are NOT verification evidence, they
     need not be listed ("plus non-verification tests" suffices).
     If ONLY non-verification tests changed: "Non-verification tests only."
     If no tests changed: "None."
     (The ## Verification checklist below records HOW this PR was verified;
     this section records WHICH requirement-tagged tests changed.) -->

- None

## SDD Deviation

<!-- Does this implementation deviate from the SDD as written (component
     boundaries, interfaces, behavior described in SDD sections)?
     Deviation is not a nitpick — it is a design-change trigger (SOP-003 §13)
     and must be visible before merge.
       No.
     or
       Yes — SDD-09 describes X; this implements Y because Z. Flagged to Design Owner.
     -->

- No

## New Dependencies

<!-- Required whenever this PR changes a dependency manifest or lockfile
     (package.json / lockfiles, Cargo.toml/.lock, gradle files, Package.swift/.resolved).
     One line per NEW or UPGRADED dependency:
       name@version — runtime|dev — device path? — purpose — license — maintenance note — known CVEs/advisories checked
     If the manifest change introduces no new/upgraded dependency, say why:
       "None — lockfile refresh only, no dependency changes."
     Internal @eiro/* packages count. (CMP §10) -->

- None

## Verification

<!-- State what was checked and where evidence lives. -->

- [ ] Build/typecheck
- [ ] Unit tests
- [ ] Integration tests
- [ ] Static analysis / lint
- [ ] Dependency or SBOM impact reviewed
- [ ] Secret scan / cybersecurity impact reviewed
- [ ] DHF document review only
- [ ] Other:

## Thorne Boundary Check

- [ ] This PR does not introduce Eiro-authored clinical interpretation.
- [ ] This PR does not introduce safety detection, safety flagging, triage, crisis prediction, priority ranking, patient-status assignment, or treatment recommendation.
- [ ] This PR does not introduce PHQ-9 item 9 default alerting, urgent notification, 24-hour, push, or on-call alert behavior.
- [ ] This PR does not change the meaning, priority, salience, or safety significance of device output from a non-device surface.
- [ ] If this is pre-design scaffolding, it stays within CMP §7 and does not implement clinical device behavior.

## Reviewer Notes

<!-- Call out risk, traceability gaps, follow-up DHF updates, or known limitations. -->

</details>

<!--
──────────────────────────────────────────────────────────────────────────
ACCESSIBILITY SECTION ↓  — only required if this PR changes user-facing UI.

This cuts a DIFFERENT axis from the device lane above: it applies to any UI
change (device or non-device) and not at all to non-UI changes. Baseline
standard: WCAG 2.2 AA. These are the human-judgment checks a reviewer confirms
by hand — the machine-checkable items live in the enforcers, not here.

This section IS the source of truth for these checks — to add or change one,
edit here. See design/accessibility.md in thorne-product for rationale, WCAG
mapping, and context (that doc carries an illustrative example, not the home).

• No user-facing UI change? Tick "N/A" below and you're done.
• Changed UI? Tick "changes user-facing UI" and confirm each item.
──────────────────────────────────────────────────────────────────────────
-->

<details>
<summary><b>Accessibility</b> — fill in only for user-facing UI changes</summary>

## Accessibility

- [ ] This PR changes user-facing UI
- [ ] N/A — no user-facing UI change

<!-- If UI changed, confirm each item for the surfaces this PR touches (WCAG 2.2 AA): -->

- [ ] **SR-01** — Every screen is operable and reads coherently under the platform screen reader (VoiceOver / TalkBack) — including status / loading / error changes being announced, not silent.
- [ ] **SR-02** — Reading / traversal order matches the visual and logical order.
- [ ] **CD-03** — Each image's content description conveys the information/purpose it carries — not the file name or "image".
- [ ] **FORM-01** — Form fields have meaningful, persistent labels (not placeholder-only); validation errors clearly say what's wrong, are tied to their field, and are announced.
- [ ] **TYPE-02** — Layout stays usable at the largest supported font setting — no clipping, overlap, or lost actions.
- [ ] **TYPE-03** *(web)* — Content reflows without horizontal scrolling at 320 CSS px / 400% zoom.
- [ ] **COLOR-03** — Color is never the *only* way information is conveyed (status/error/selection also carry text, icon, or shape).
- [ ] **FOCUS-01** — All interactive elements are reachable and operable by keyboard / switch / external control with no traps, and focus is managed on route / dialog changes (moved into dialogs, restored on close).

</details>
