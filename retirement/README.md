# Declaration-check retirement rollout

This directory records the proposed configuration changes for [epic #43](https://github.com/eiro-inc/.github/issues/43). These are review artifacts, not evidence that retirement has happened. Do not apply settings until the policy and caller PRs have the required human approvals.

## Merge order

1. Merge the QMS policy/determination PR. Then, with the DHF PR approved, apply the reviewed DHF ruleset change immediately before merging its closeout/CMP and caller-removal PR, using the preservation/re-read checks in steps 2–3. The DHF PR also deletes a caller, so do not merge it while its retired status is still required. Existing owner review and controlled document approval remain.
2. For each of the eight active callers, review its PR and `required-checks/<repo>.json`. Re-read classic branch protection and effective rules immediately before applying a change. Remove only `thorne-pr-boundary-check`; preserve all other required contexts and their App bindings, strictness, reviews, signing, bypass restrictions and history protections. The captured UI repositories do not currently require `thorne-a11y-check`; re-check live rules and remove only that declaration status if it was subsequently added. Do not remove actual accessibility test jobs.
3. With the caller PR approved, remove the retired requirement and merge that caller/template PR in the same maintenance window. Do not wait until after deleting the workflow: a required status with no producer can strand the PR. Do not insert an always-green compatibility status. Re-read effective rules and retain before/after exports with the merged commit and remaining CI results.
4. Merge organization PR #44 once active consumers use their local short template and no active caller depends on the shared form. Then merge the compliance-tools PR; its existing drift check compares the fallback copy to the organization template and is expected to match at that point. Local short copies let consumers migrate independently before the organization default changes.
5. Check a representative normal PR and dependency-update PR in each affected repository. Confirm the short body is accepted, remaining checks run, and no retired required status remains. Record evidence in #43. Leave the epic open until this is complete.

The seven classic-protection files contain exact PATCH payloads under `after`. The DHF uses repository ruleset 16365542: its file is a diff of one rule, not a complete PUT payload. Retrieve the full ruleset and change only its required-status-check list; do not overwrite the ruleset with this partial artifact. If the live configuration differs from `before`, regenerate and review the change rather than replaying a stale snapshot.

## Retained material

Archived `thorne-patient-web` and `thorne-clinician-web` remain untouched. Before unarchiving, retire their old declarations or establish the applicable live workflow. Old shared action implementations, tests and release tags remain readable for historical pins; they are deprecated and get no new rollout. No replacement questionnaire or policy-revision validator is introduced.

`thorne-lanes.yml` remains where other tooling (including source traceability) reads it. Removing the PR-body checker does not remove source-code tests, owner review, dependency scanning or build checks. The accessibility review guidance moves to `thorne-product/design/accessibility.md`; human checks are chosen for the actual UI change.

## Field-dependency assessment

The old boundary action checks the presence/form of declarations; it never verifies qualified review or the code's medication-adherence behavior. Removing DHF Trace and Safety Class therefore removes form enforcement, not an implemented specialist-review route. POL-006 retains targeted qualified non-author current-head review through ordinary PR review. Relevant product tests and release obligations remain. The accepted tradeoff is losing a universal author reminder, addressed by clear review responsibility and actual requirements/tests rather than a new mandatory form.

Retirement does not close HAZ items, safety findings, enrollment conditions, billing readiness, or the entire DHF programme. REC-050 remains historical assurance of the old intended use, and the software inventory tracks actual remaining reliance until the last caller is migrated.
