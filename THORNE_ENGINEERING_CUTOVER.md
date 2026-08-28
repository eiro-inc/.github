# Thorne Engineering Cutover

**Decision date:** 2026-08-24

**Operational cutover:** completed 2026-08-27 by [DR-0012 Revision 1 and DDP Revision 23](https://github.com/eiro-inc/thorne-dhf/pull/275), after [REC-116 Revision 1](https://github.com/eiro-inc/eiro-qms/pull/705) became effective

**Owner:** Forrest Laine

This is the short operating guide for engineering under Eiro's controlled closeout of the FDA-submission design programme and the Fall 2026 commercial plan. It is not a regulatory classification opinion and does not replace the controlled authority records. If it conflicts with REC-116 Revision 1, DR-0012 Revision 1, or DDP Revision 23, those records control.

## What changed at cutover

- Do not create new submission-directed DHF requirements, design outputs, architecture decisions, TRM entries, verification-renewal work, validation plans, or phase-exit material.
- Keep tagging tests that verify a requirement with `@verifies SRS-NN-MM`. The tag now points to `thorne-product/design/product-requirements.md`, being issued in [thorne-product#182](https://github.com/eiro-inc/thorne-product/pull/182). Until that migration merges, retain existing tags and identifiers without creating new DHF work. After cutover the tag carries no DHF obligation, no traceability-matrix administration, and no merge gate; it remains because knowing which test covers which requirement is useful engineering practice.
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

## Review routing

Until [POL-006](https://github.com/eiro-inc/eiro-qms/blob/main/policies/POL-006-thorne-product-boundary.md) and [`thorne-safety-reviewers`](https://github.com/eiro-inc/eiro-qms/blob/main/records/product-safety/thorne-safety-reviewers.md), being issued in [eiro-qms#704](https://github.com/eiro-inc/eiro-qms/pull/704), are effective, retain the existing Thorne boundary check. Apply documented review against the exact A001/Q261559 envelope and HAZ Revision 12. The Product Boundary Owner obtains any required counsel review and records its basis; a qualified reviewer approves the current head. In addition to ordinary owner review, flag any PR touching one of these areas before merge:

- medication adherence;
- crisis paths or no-detection copy/behavior;
- score calculation, score display, instrument rules, or clinical-output ML;
- alert, flag, urgency, priority, salience, or patient-status behavior; or
- data-integrity and money paths, including activation, consent, day/time/contact ledgers, audit history, or billing packets.

Once effective, POL-006 §6 is the Safety-Path Review Checklist and `thorne-safety-reviewers` supplies the qualified reviewer. Such a PR requires that reviewer's approval on the current PR head. A general owner approval or author self-attestation does not satisfy this route.

Ordinary test-file changes do not require a named V&V merge approver. Expressly routed safety and money-path changes do require their qualified reviewer's approval on the current head. This is the two-part successor principle retained from [ADR-0018](https://github.com/eiro-inc/thorne-dhf/blob/main/04-outputs/decisions/ADR-0018-verification-evidence-path-review.md).

## Pull requests during the overlap

The existing organization template and pinned boundary action still mechanically require four device-era fields in some repositories: **DHF Trace**, **Affected Device Software Items**, **Safety Class**, and **SDD Deviation**. Complete them only as needed to pass the still-live gate; do not generate new DHF artifacts merely to satisfy them. The Accessibility section and accessibility-review workflow remain. The four named fields and submission-directed verification-trace workflows are removed only after:

1. the QMS and DHF authority records are effective — completed by REC-116 Revision 1 and DR-0012 Revision 1/DDP Revision 23;
2. POL-006, its §6 routing, the safety-reviewer registry, and the Product Safety Risk Register are effective and deliberately tested; and
3. the Product Boundary Owner records a one-time checklist in the coordinated removal PR showing that (a) each live safety rule and supporting test is linked from the Product Safety Risk Register and first-enrollment Product Safety Release Record, and (b) each billing rule and supporting test is linked from the versioned evidence index under `thorne-product/design/`. The check passes only when every rule has an owner, live source, implementation/test anchor, and no unresolved control gap; the removal PR and its linked evidence are the retained record.

This temporary overlap is intentional. It prevents a gap in boundary or safety review while allowing the team to stop expanding the submission file.

This PR publishes the guide and can close C3. It does not itself close C1 or all of MR-3 because it does not remove the four fields or pinned actions. [eiro-qms#715](https://github.com/eiro-inc/eiro-qms/issues/715) and [eiro-qms#708](https://github.com/eiro-inc/eiro-qms/issues/708) remain open through the coordinated removal and validation wave.

## Keeping the live records honest

The successor product requirements (`thorne-product/design/product-requirements.md`) and Thorne Product Safety Risk Register are controlled knowledge sources, not universal merge gates. The named-reviewer routing above has the teeth. Because the records do not block every merge, someone must deliberately check them before each release:

1. Did the release change behavior described by a product requirement? If yes, update the requirement in the same release or open an issue that identifies the inaccurate requirement and blocks reliance on it.
2. Did the release change, add, or remove a control cited by a Product Safety Risk Register entry, or introduce a new way the product could mislead a clinician or patient? If yes, the Product Safety Owner reviews and updates the register before release.
3. Neither answer is “no” by default. “No” means the release reviewer checked and recorded the result.

Forrest Laine owns the product-requirements set. Colin Walsh is the primary Product Safety Owner and Ofer Dagan the alternate under `thorne-safety-reviewers` once that registry is effective.

## Launch gates are unchanged

The cutover does not authorize external claims, production PHI, enrollment, or live-claim support. REC-116 Decision 9 controls the sequence directly:

- The [claims inventory and initial claims review](https://github.com/eiro-inc/eiro-qms/tree/main/records/claims) (forthcoming) precede external claims.
- [POL-004](https://github.com/eiro-inc/eiro-qms/blob/main/policies/POL-004-hipaa.md) (forthcoming) and the [whole-estate Security Risk Assessment](https://github.com/eiro-inc/eiro-qms/blob/main/records/security/thorne-security-risk-assessment.md) (forthcoming) precede production PHI.
- Authorized F1 and F20 closure in the [first-enrollment Product Safety Release Record](https://github.com/eiro-inc/eiro-qms/tree/main/records/product-safety) precedes enrollment.
- The controlled [counsel regulatory-posture opinion](https://github.com/eiro-inc/eiro-qms/tree/main/records/regulatory) and [billing rehearsal decision](https://github.com/eiro-inc/eiro-qms/tree/main/records/billing) (both forthcoming) precede live-claim support.

These correspond to G1–G5 in the Fall 2026 commercial plan; the controlled homes above, not the working-plan shorthand alone, govern release.

## Questions and exceptions

- Product-boundary or transition-scope question: Forrest Laine.
- HFE/IRB or clinical-safety question: Colin Walsh.
- V&V evidence or controlled-DHF question: Ofer Dagan.
- Any proposed exception: stop and record it through the applicable controlled decision before implementation.
