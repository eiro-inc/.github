# Boundary retirement inventory and C1 analysis

Captured: 2026-09-09T18:00:38.709794+00:00. All 35 organization repositories visible to the authenticated account were inspected at their recorded default-head SHA.

## Active and archived callers

| Repository | State | Action reference | Effective boundary requirement |
|---|---|---|---|
| `eiro-inc/thorne-product` | Active | `- uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@73ffa92185a510e8fbbcb203468142a68731be3e # lane-aware + CMP §10 New Dependencies gate (.github#15)` | `thorne-pr-boundary-check` |
| `eiro-inc/thorne-patient-android` | Active | `- uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@4490100c813089577802d967aa91f82b4841bfae # lane-aware + CMP §10 New Dependencies gate (.github#15)` | `thorne-pr-boundary-check` |
| `eiro-inc/thorne-core` | Active | `- uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@4490100c813089577802d967aa91f82b4841bfae # lane-aware + CMP §10 New Dependencies gate (.github#15)` | `thorne-pr-boundary-check` |
| `eiro-inc/thorne-dhf` | Active | `- uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@fe4261b0af49a45da3b8cf37b3dd3bf9b124864c # v1.0.0` | `thorne-pr-boundary-check` |
| `eiro-inc/thorne-web` | Active | `- uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@main` | `thorne-pr-boundary-check` |
| `eiro-inc/thorne-backend` | Active | `- uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@bc1958308f14617f84215bc8ee258c771bad0ae3 # lane-aware checker (v1.1.0 tag pending)` | `thorne-pr-boundary-check` |
| `eiro-inc/thorne-patient-ios` | Active | `- uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@4490100c813089577802d967aa91f82b4841bfae # lane-aware + CMP §10 New Dependencies gate (.github#15)` | `thorne-pr-boundary-check` |
| `eiro-inc/thorne-design-tokens` | Active | `- uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@4490100c813089577802d967aa91f82b4841bfae # lane-aware + CMP §10 New Dependencies gate (.github#15)` | `thorne-pr-boundary-check` |
| `eiro-inc/thorne-patient-web` | Archived | `- uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@d7ab73906ce97a642590a59cbafe7d378e971401 # main @ 2026-07-07` | `thorne-pr-boundary-check` |
| `eiro-inc/thorne-clinician-web` | Archived | `- uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@fe4261b0af49a45da3b8cf37b3dd3bf9b124864c # v1.0.0` | `thorne-pr-boundary-check` |

## Unknowns

The JSON retains API errors and their endpoint. In particular, a 404 from classic protection is not silently interpreted as absence: it can also reflect access limits. The effective-rules endpoint is inspected independently. Resolve unknowns before certifying final removal.

- `eiro-inc/document-review`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/.github`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/eiro-security`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/eiro-aws`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/eiro-website`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/aws-security-baseline`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/Eiro-wiki`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/Eiro-iOS`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/treatment-evidence-mining`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/mdd-cds`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/eiro-rule-library`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/ClaimsData`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/network-bh-map`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/rtm-wiki`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/MDDMDP.jl`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/mdd-qlearning`: classic_protection: gh: Branch not protected (HTTP 404)
- `eiro-inc/Eiro-Clinical`: No default branch
- `eiro-inc/CONFIDENCEBOUNDS.jl`: classic_protection: gh: Branch not protected (HTTP 404)

## C1: dependency analysis

The existing action validates author declarations. Its `validate()` routine consumes DHF Trace, Affected Device Software Items and Safety Class; `determine_lane()` uses the changed-file list and base-branch lane configuration. It does not fetch PR reviews, resolve POL-006 reviewer domains, or validate qualified current-head approval. Those fields therefore do not implement the new medication-adherence safety-review route. Removing them without a successor still loses the existing declaration gate; that is not proof that retirement is safe.

POL-006 §6 routes medication-adherence changes through its explicit §4 question and the Product Boundary Owner/counsel route. The successor must consume that independent answer and trusted path routing, not infer it from a device-function checkbox or safety class. C1 is ready for owner confirmation only after a deliberate adherence-change test demonstrates that this route still fails without its required qualified non-author current-head approval after all four legacy fields are absent. That live test and owner confirmation are pending.

## Scope dispositions

- Eight active callers require a coordinated per-repository decision: seven product/shared-product repositories and `thorne-dhf`, whose document-closeout scope differs from production changes. Do not blindly apply a product-code gate to the DHF or delete its required check without a recorded disposition.
- `thorne-patient-web` and `thorne-clinician-web` are archived. Preserve their pins and history; record how a future unarchive restores applicable protection.
- Search results in `thorne-vv-tooling`, QMS records and compliance tooling do not necessarily represent executable callers. Retain historical validation and retire only live dependencies.
- `bump-design-tokens` generators, `dependabot-thorne-boundary`, local/inherited templates, and template-drift checks need coordinated changes. Preserve independent accessibility checks.

## Evidence limits

This capture proves repository configuration, not successful successor enforcement or controlled approval. It scans workflow/configuration Markdown and YAML plus the shared guide/README; inspect scripts, skills and all other generated PR-body sources separately before closure. It covers default branches; retained release tags are historical artifacts and must remain available.
