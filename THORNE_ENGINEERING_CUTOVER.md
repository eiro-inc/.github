# Thorne Engineering Cutover

**Decision date:** 2026-08-24  
**Operational cutover:** approval and merge of the QMS transition PR, followed by approval and merge of Thorne DR-0012 and its DDP revision  
**Owner:** Forrest Laine

This is the short operating guide for engineering while Eiro moves from the FDA-submission design programme to the Fall 2026 commercial plan. It is not a regulatory classification opinion and does not replace the controlled authority records. If it conflicts with the approved QMS transition or DR-0012, those records control.

## What changes at cutover

- Do not create new submission-directed DHF requirements, design outputs, architecture decisions, trace rows, `@verifies` mappings, verification-renewal work, validation plans, or phase-exit material.
- Build launch work in the engineering and product repositories using ordinary issues, specifications, tests, code review, security review, accessibility review, and release evidence.
- Do not treat P4 as complete, enter P5/P6, or describe the product as FDA approved, cleared, exempt, confirmed, or otherwise accepted by FDA.
- PRs `thorne-dhf#271`, `#273`, and `#274` are not new authority. They are to close unmerged after the successor engineering PR is linked.

## Work that may continue in the old DHF

The DHF remains writable only for the closeout scope in the approved DDP revision:

- complete and approve UE-02-E round-two results, session records, consent/CAPA/IRB reconciliation, and finding dispositions;
- preserve the exact as-filed A001 package, FDA's Q261559 response, and their provenance;
- correct or harden an existing record so the point-in-time file is accurate;
- migrate a still-binding safety, product-boundary, security, architecture, or operating obligation to its live successor; and
- prepare controlled withdrawal, audit-trail export, archive, restore testing, or documented re-entry.

A DHF change outside this list needs a revised DR-0012 before work starts. Suspension does not close F1, F20, a CAPA, an IRB duty, or any safety finding.

## Product rules that remain live

The transition removes submission paperwork, not the product boundary.

1. **Medication-adherence floor.** Medication-adherence tracking is the sole asserted device-function basis for the commercial RTM strategy. It must remain real, prominent, and used by every activated patient. Removing it, making it optional, de-emphasizing it, or materially changing it requires Product Boundary Standard and counsel review.
2. **A001 ceiling.** Do not expand product behavior or claims beyond the exact A001/Q261559 and counsel envelope. Transport, display, deterministic published scoring, symptom capture, and safety-screening flags are not offered as the RTM device predicate.
3. **No new clinical interpretation.** Do not add Eiro-authored salience, severity, urgency, patient-status assignment, triage, treatment recommendation, or ML in a clinical-output path without boundary, safety, instrument-rights, and claims review.
4. **Preserve the alert envelope and score fidelity.** Crisis/no-detection behavior, score calculation or display, and validated-instrument rules are not ordinary copy or refactor changes.
5. **Preserve data and money-path integrity.** Activation, adherence days, time, contacts, consent, audit history, packet generation, and reconciliation must remain deterministic, attributable, and testable.

## Review routing

Until the controlled Product Boundary Standard, Safety-Path Review Checklist, path map, and qualified-reviewer register are effective, retain the existing Thorne boundary check. In addition to ordinary owner review, flag any PR touching one of these areas before merge:

- medication adherence;
- crisis paths or no-detection copy/behavior;
- score calculation, score display, instrument rules, or clinical-output ML;
- alert, flag, urgency, priority, salience, or patient-status behavior; or
- data-integrity and money paths, including activation, consent, day/time/contact ledgers, audit history, or billing packets.

Such a PR requires the qualified reviewer named by the successor register, and that approval must apply to the current PR head. Until the register is issued, do not infer that a general owner approval or author self-attestation satisfies this route: escalate to the transition owner for an explicit reviewer assignment.

## Pull requests during the overlap

The existing organization template and pinned boundary action still mechanically require device-era fields in some repositories. Complete those fields only as needed to pass the still-live gate; do not generate new DHF artifacts merely to satisfy them. The old fields and verification-trace workflows are removed only after:

1. the QMS and DHF authority PRs merge;
2. the controlled floor/ceiling and named-reviewer successor is live and deliberately tested; and
3. a one-time overlap check confirms that any test supporting a live safety or money-path rule is linked from its successor evidence index.

This temporary overlap is intentional. It prevents a gap in boundary or safety review while allowing the team to stop expanding the submission file.

## Launch gates are unchanged

The cutover does not authorize external claims, production PHI, enrollment, or live-claim support. Those events remain blocked by G1–G5 in the Fall 2026 commercial plan, including claims control, POL-004 and the whole-estate security risk assessment, F1/F20 closure, and billing rehearsal evidence.

## Questions and exceptions

- Product-boundary or transition-scope question: Forrest Laine.
- HFE/IRB or clinical-safety question: Colin Walsh.
- V&V evidence or controlled-DHF question: Ofer Dagan.
- Any proposed exception: stop and record it through the applicable controlled decision before implementation.
