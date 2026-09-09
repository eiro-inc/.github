# Thorne Engineering Cutover

**Decision date:** 2026-08-24

**Operational cutover:** completed 2026-08-27 by [DR-0012 Revision 1 and DDP Revision 23](https://github.com/eiro-inc/thorne-dhf/pull/275), after [REC-116 Revision 1](https://github.com/eiro-inc/eiro-qms/pull/705) became effective

**Owner:** Forrest Laine

This is the short operating guide for engineering under Eiro's controlled closeout of the FDA-submission design programme and the Fall 2026 commercial plan. It is not a regulatory classification opinion and does not replace the controlled authority records. If it conflicts with the current approved revisions of REC-116, DR-0012, or DDP, those records control.

## What changed at cutover

- Do not create new submission-directed DHF requirements, design outputs, architecture decisions, TRM entries, verification-renewal work, validation plans, or phase-exit material.
- Retain useful requirement/test links. Existing `@verifies SRS-NN-MM` tags resolve as history in `thorne-product/design/legacy-srs-requirements.md`; re-decided requirements use `thorne-product/docs/requirements.md` and `REQ-` identifiers. No DHF artifact or TRM administration is required for ordinary engineering.
- Build launch work in the engineering and product repositories using ordinary issues, specifications, tests, code review, security review, accessibility review, and release evidence.
- Do not treat P4 as complete, enter P5/P6, or describe the product as FDA approved, cleared, exempt, confirmed, or otherwise accepted by FDA.
- The bounded final pre-cutover hardening set has merged: `thorne-dhf#271` issued VVP-01 Revision 15, `#273` issued ADR-0018 Revision 1, and `#274` issued CMP Revision 10. Their content is retained history, not authority to start new submission work.

## Work that may continue in the old DHF

The DHF remains writable only for the closeout scope in the approved DDP revision:

- complete and approve UE-02-E round-two results, de-identified session records, consent-deviation/CAPA reconciliation, required IRB records, and finding dispositions;
- preserve the exact as-filed A001 package, FDA's Q261559 response, and their provenance;
- correct or harden an existing record so the point-in-time file is accurate;
- migrate a still-binding safety, product-boundary, security, architecture, or operating obligation to its live successor; and
- prepare controlled withdrawal, audit-trail export, archive, restore testing, or documented re-entry.

A DHF change outside this list needs a revised DR-0012 before work starts. Suspension does not close F1, F20, a CAPA, an IRB duty, or any safety finding.

## Product rules that remain live

The transition removes submission paperwork, not the product boundary.

1. **Medication-adherence floor.** Medication-adherence functionality is the candidate device-function basis in the commercial RTM hypothesis, pending counsel's feature-fit and device-status conclusions. It must remain real and prominent in the activated-patient experience. Removing it, making it optional, de-emphasizing it, materially changing it, or adding dosing-schedule behavior to pursue product code NXQ requires Product Boundary Standard and counsel review. Do not present NXQ fit or RTM eligibility as settled.
2. **A001 ceiling.** Do not expand product behavior or claims beyond the exact A001/Q261559 and counsel envelope. Transport, display, deterministic published scoring, symptom capture, and safety-screening flags are not offered as the RTM device predicate.
3. **No new clinical interpretation.** Do not add Eiro-authored salience, severity, urgency, patient-status assignment, triage, treatment recommendation, or ML in a clinical-output path without boundary, safety, instrument-rights, and claims review.
4. **Preserve the alert envelope and score fidelity.** Crisis/no-detection behavior, score calculation or display, and validated-instrument rules are not ordinary copy or refactor changes.
5. **Preserve data and money-path integrity.** Activation, adherence days, time, contacts, consent, audit history, packet generation, and reconciliation must remain deterministic, attributable, and testable.

## Pull requests and review

Use the short PR template: Summary, Testing, and optional Reviewer notes. Explain the actual change and test results; link an issue when useful. Do not require device-lane, DHF-trace, safety-class, boundary or accessibility declarations. For consequential clinical, scoring, data-integrity or billing changes, obtain the relevant qualified non-author review through the existing PR process under POL-006 §6. Preserve owner review and useful tests. Ordinary test-file changes do not require a named V&V merge approver. Expressly routed safety and money-path changes require their qualified reviewer's approval on the current head (DR-0012 §4.2; REC-116 Decision 6).

The retirement PR set in [#43](https://github.com/eiro-inc/.github/issues/43) aligns POL-006 and the controlled cutover records, removes declaration workflows and their required statuses, and updates local templates and automated PR bodies. Merge the controlled changes first and remove only the retired status requirements alongside each caller migration. Publish the shared short template after consumers are compatible. Retain historical action releases; do not deploy a replacement form checker.

Accessibility review belongs with the actual UI change and relevant testing. The retired accessibility declaration checker checked boxes, not rendered UI. Screen-reader, keyboard, text scaling, contrast, and other applicable checks remain engineering work.

The controlled retirement determination is [REC-122 §4.2](https://github.com/eiro-inc/eiro-qms/blob/main/records/REC-122-thorne-dhf-withdrawal-record.md), with the implementation addendum in [REC-116 §10](https://github.com/eiro-inc/eiro-qms/blob/main/records/management-review/REC-116-thorne-commercial-cutover.md). These revisions must be approved and effective through [eiro-qms#760](https://github.com/eiro-inc/eiro-qms/pull/760) before any declaration check is retired. The determination accounts for each removed declaration check and retained substantive control. It does not close safety findings or authorize enrollment, PHI use, or billing. The risk register remains release knowledge rather than a universal merge gate.

## Keeping the live records honest

The live product requirements (`thorne-product/docs/requirements.md`) and Thorne Product Safety Risk Register are controlled knowledge sources, not universal merge gates. The named-reviewer routing above has the teeth. Because the records do not block every merge, someone must deliberately check them before each release:

1. Did the release change behavior described by a product requirement? If yes, update the requirement in the same release or open an issue that identifies the inaccurate requirement and blocks reliance on it.
2. Did the release change, add, or remove a control cited by a Product Safety Risk Register entry, or introduce a new way the product could mislead a clinician or patient? If yes, the Product Safety Owner reviews and updates the register before release.
3. Neither answer is “no” by default. “No” means the release reviewer checked and recorded the result.

Forrest Laine owns the product-requirements set. Colin Walsh is the primary Product Safety Owner and Ofer Dagan the alternate under `thorne-safety-reviewers` once that registry is effective.

## Launch gates are unchanged

The cutover does not authorize external claims, production PHI, enrollment, or live-claim support. [REC-116 Decision 9](https://github.com/eiro-inc/eiro-qms/blob/main/records/management-review/REC-116-thorne-commercial-cutover.md) controls the sequence directly. The paths below are the authoritative homes assigned by REC-116 §5.1; items marked forthcoming are intentionally not linked until their controlled records exist.

- The claims inventory and initial claims review (`eiro-qms/records/claims/`, forthcoming) precede external claims.
- POL-004 (`eiro-qms/policies/POL-004-hipaa.md`, forthcoming) and the whole-estate Security Risk Assessment (`eiro-qms/records/security/thorne-security-risk-assessment.md`, forthcoming) precede production PHI.
- Authorized F1 and F20 closure in the first-enrollment Product Safety Release Record (`eiro-qms/records/product-safety/`, forthcoming) precedes enrollment.
- The controlled counsel regulatory-posture opinion (`eiro-qms/records/regulatory/`, forthcoming) and billing rehearsal decision (`eiro-qms/records/billing/`, forthcoming) precede live-claim support.

These correspond to G1–G5 in the Fall 2026 commercial plan; the controlled homes above, not the working-plan shorthand alone, govern release.

## Questions and exceptions

- Product-boundary or transition-scope question: Forrest Laine.
- HFE/IRB or clinical-safety question: Colin Walsh.
- V&V evidence or controlled-DHF question: Ofer Dagan.
- Any proposed exception: stop and record it through the applicable controlled decision before implementation.
