# Epic: retire the Thorne declaration checker and simplify pull requests

The current boundary checker verifies form completion, not product correctness or the quality of review. Its device-era declarations add friction after suspension of the submission programme. Retire that gate and adopt a short PR template: Summary, Testing, and optional Reviewer notes. Link an issue in Summary when useful. Do not introduce a replacement universal questionnaire, policy-revision field, or bespoke safety-review gate.

Keep ordinary code review, specialist input for consequential changes, and tests that check actual behavior. Product constraints and review responsibilities belong in concise engineering guidance and applicable requirements; PR authors should explain the specific change rather than recite them on every PR.

## Work

- [x] Inventory all 35 visible organization repositories and capture default-head workflows and effective branch rules. Eight active repositories have legacy callers; two archived repositories retain historical callers. Preserve unknown API/configuration results explicitly.
- [x] Prepare the short organization PR template.
- [ ] Revise the relevant language in POL-006, the reviewer registry, and engineering cutover guidance so they describe the agreed review approach and explicitly permit retirement without a replacement declaration gate. Use the normal document-review process; do not misrepresent a draft as approved.
- [ ] Document where specialist review is useful: clinical interpretation/scoring, patient-data integrity, and billing behavior. Prefer existing review mechanisms. Add automation only for a concrete failure it can actually detect.
- [ ] Remove the legacy required-check entries and callers in a coordinated rollout across active repositories. Account for both classic protection and rulesets. Give the DHF closeout repository its own scope disposition; leave archived history intact.
- [ ] Align inherited/local templates, generated bot PR bodies, dependency injection, drift checks, compliance-tool guidance, and open template PR #42. Stop generating obsolete declarations.
- [ ] Resolve the existing accessibility declaration check's dependency on the long template before deploying the short template to UI repositories. Preserve useful accessibility tests and review; do not replace the deleted block with another mandatory form by default.
- [ ] Retain historical action releases and validation evidence; update the software inventory and disposition obsolete maintenance tickets after their consumers are retired.
- [ ] Verify representative human and dependency-update PRs can use the short template, all independent useful checks still run, and no removed workflow remains required. Record per-repository evidence and close the related cutover actions only when their actual remaining scope is complete.

## Rollout evidence

The template must be understandable without consulting a policy, have no mandatory checkbox list, and allow a short explanation proportionate to the change. No new checker enforces its headings or prose.

The existing boundary action intentionally rejects this shorter template. The accessibility declaration action also requires its old checkbox block on UI changes. Prepare the template now, but coordinate its publication with those dependencies so the rollout does not strand PRs. A successful rollout is demonstrated by real PRs and before/after rule exports, not a synthetic always-green replacement status.

The recorded safety/billing overlap requirements and automation-retention language in the existing cutover documents must be explicitly revised or dispositioned as part of retirement. Do not turn unrelated first-enrollment deliverables into implementation dependencies merely because the earlier plan bundled them together. Preserve actual product obligations and open findings, and explain which review/test mechanisms address them.

## Related work

This epic covers the checker/template portion of [eiro-qms#708](https://github.com/eiro-inc/eiro-qms/issues/708) and the related field-dependency question in [#715](https://github.com/eiro-inc/eiro-qms/issues/715), under [#706](https://github.com/eiro-inc/eiro-qms/issues/706). Their wording needs reconciliation with this scope; no closure is implied by agreeing on a template.

Maintenance to disposition: `.github#11`, `#12`, `#16`, `#29`, `#35`, `#37`; `eiro-qms#484`; `thorne-backend#94`; generated PR bodies in `thorne-design-tokens#118`. Review the accessibility work in `.github#36` separately for surviving value. Coordinate `.github#42` to avoid reintroducing retired text.

## Prepared PR set

All PRs are prepared; merges and live required-check changes remain pending review.

| Repository | PR |
|---|---|
| .github | [.github#44](https://github.com/eiro-inc/.github/pull/44) |
| eiro-compliance-tools | [eiro-compliance-tools#72](https://github.com/eiro-inc/eiro-compliance-tools/pull/72) |
| eiro-qms | [eiro-qms#760](https://github.com/eiro-inc/eiro-qms/pull/760) |
| thorne-backend | [thorne-backend#516](https://github.com/eiro-inc/thorne-backend/pull/516) |
| thorne-core | [thorne-core#232](https://github.com/eiro-inc/thorne-core/pull/232) |
| thorne-design-tokens | [thorne-design-tokens#123](https://github.com/eiro-inc/thorne-design-tokens/pull/123) |
| thorne-dhf | [thorne-dhf#292](https://github.com/eiro-inc/thorne-dhf/pull/292) |
| thorne-patient-android | [thorne-patient-android#536](https://github.com/eiro-inc/thorne-patient-android/pull/536) |
| thorne-patient-ios | [thorne-patient-ios#56](https://github.com/eiro-inc/thorne-patient-ios/pull/56) |
| thorne-product | [thorne-product#235](https://github.com/eiro-inc/thorne-product/pull/235) |
| thorne-web | [thorne-web#114](https://github.com/eiro-inc/thorne-web/pull/114) |

Merge QMS #760 first. Apply the reviewed DHF ruleset removal immediately before merging its approved #292. Migrate the remaining callers by removing only their retired required status immediately before merging each approved caller PR. Publish #44 after caller compatibility, then compliance-tools #72 after #44 and product #235. The complete runbook and configuration diffs are in #44.

ADR-0003/0004/0010 remain retained pending a separate rule-by-rule disposition. Checker retirement does not retire two web deployables, directional dependencies, owner-review protections, or authenticated/raw/read-only own-data access and audit obligations. Prefer adopting surviving rules into existing live engineering/service docs and SOP-005 rather than creating three duplicate successor ADRs.

## Independent review and validation

An independent agent reviewed all 11 published PRs and found no outstanding blocking issues after fixes. The review covered controlled-policy consistency, short-template consumers, actual versus declaration-only checks, generated PR bodies, retained legacy test coverage, and exact required-status removals. Validation: shared actions 182 passed / 1 skipped; compliance tools 114 passed; backend workflow guards 20 passed; changed workflows pass Actionlint; five updated skills pass quick_validate. Ofer review requests follow this independent pass.

PR #42 was reviewed separately and approved at `551c9f18e25beac5394fa7f3018cad3f0f11e18d`: comment-only citation correction with unchanged rendered content and validator behavior. It does not disposition ADR-0010.
