# GitHub Templates for Eiro Inc. QMS

This repository provides organization-default GitHub templates and reusable workflows for Eiro Inc. repositories.

> **Thorne transition (decision date 2026-08-24):** The FDA-submission design programme is moving to controlled closeout. Engineering should use the [Thorne Engineering Cutover](THORNE_ENGINEERING_CUTOVER.md) as the team-facing operating guide once the authority PRs named there merge. The device-era details below describe still-installed legacy checks during the no-gap overlap; they are not instructions to expand the suspended DHF.

## Thorne Pull Request Template

The organization-level pull request template includes Thorne-specific sections for:

- Thorne scope classification.
- DHF trace anchors.
- Affected device software-item (`ARC-NN`) and safety-class mapping.
- Verification evidence.
- Boundary confirmations for the device/non-device membrane.

Repositories inherit this template unless they define a repository-local `.github/pull_request_template.md`.

The automatic **device lane** and the declared **product-function scope** are
separate axes. A PR can correctly select `Non-device function` plus
`Multiple-Function impact assessment` while using the device lane and naming an
unsegregated affected item such as `ARC-04 — Class C`. Safety class follows the
affected software item; “C-adjacent” is not a safety class.

Internal build, test, deployment, and lifecycle tooling is neither a device nor
a non-device product function merely because its files select the device lane.
Such a PR selects `DHF/QMS artifact`, traces the tooling and its consuming use to
CMP §§4.1, 6, and 9, identifies any affected ARC item, and selects Safety Class
`N/A` when no device software item is affected.

## Composite Actions

### Thorne PR Boundary Check

`.github/actions/thorne-pr-boundary-check` validates that a pull request using the organization template has completed the Thorne-specific sections required for its lane. Its validator (`thorne_pr_boundary_check.py`) is an importable module with unit tests (run by `test-thorne-boundary-check.yml`). The action reads the PR's changed files and the base branch's `.github/thorne-lanes.yml`: paths are device by default, and listed `non_device` globs opt paths into the light non-device lane. Repository-specific static import-boundary checks remain local to each source-code repository.

To use it in a repository, add this workflow:

```yaml
name: Thorne PR Boundary Check

on:
  pull_request:
    types: [opened, edited, synchronize, reopened, ready_for_review]

permissions:
  contents: read
  pull-requests: read

jobs:
  thorne-pr-boundary-check:
    runs-on: ubuntu-latest
    steps:
      - uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@main
```

After adding the workflow, configure the repository's branch protection or organization ruleset to require the `thorne-pr-boundary-check` status check before merge.

**DHF Trace: anchor existence (opt-in).** By default the DHF Trace section is tested for anchor *shape*, which accepts a well-formed but nonexistent id such as `SRS-77-77`. Pass a `dhf-token` to check cited ids against the controlled DHF instead (thorne-dhf#113 AC2):

```yaml
      - uses: eiro-inc/.github/.github/actions/thorne-pr-boundary-check@main
        with:
          dhf-token: ${{ secrets.DHF_READ_TOKEN }}
```

The token needs read access to `eiro-inc/thorne-dhf` and, while it is private, to `eiro-inc/thorne-vv-tooling` (the action installs the pinned `vvtrace` engine to load the DHF id namespaces). Omit the input and the action behaves exactly as before — no checkout, no install, stdlib only — so repositories adopt this one at a time rather than all at once.

Only the families the engine has a namespace loader for are checked: **SRS, SDD, ARC, IFS, HAZ**. Everything else in the anchor vocabulary — ADR, CMP, DDS, TRM, UNS, VVP, DR, the `eiro-qms` families (SOP, POL, REC, FRM), `§` references and standard citations — has no DHF namespace and continues to be accepted on shape alone.

Checkable and citable are separate things. `ARC-NN` handles are checkable, but SDD §3 records that they are not controlled document identifiers and "shall not be cited as design-input or design-output IDs" — so an ARC citation does **not** satisfy the DHF Trace requirement on its own, whether or not the id exists. It is still validated when it appears alongside a legitimate anchor, so a bogus `ARC-99` is not ignored.

Three behaviors worth knowing before enabling it:

- A cited id of a checkable family that the engine cannot classify is reported as **malformed**: the DHF writes zero-padded two-digit ids exclusively, so `HAZ-3` is flagged where `HAZ-03` passes, and `SRS-02-04-999` is flagged rather than being read as the existing `SRS-02-04`. Citations are matched case-insensitively and the family prefix is normalized, so `srs-02-04` validates as `SRS-02-04` — the check cannot be sidestepped by casing.
- URL fragments are **not** citations. A trace that links to the document it cites (`[IFS-02](…/IFS.md#ifs-02--patient-data-capture)`) has its link target ignored; only the link text is checked. An all-alpha placeholder such as `SRS-XX-YY` is treated as narrative rather than an id, because catching it would mean flagging ordinary prose like "SRS-based"; on its own it still fails the shape check.
- Once enabled, a DHF that cannot be fetched or read — or a pinned engine install that does not complete — **fails** the check rather than falling back to the shape-only test, so the gate never reports green having verified less than it was configured to. The engine is installed into a throwaway virtualenv, so a `vvtrace` that happens to exist on the runner cannot serve the check in place of the pinned build.

**Pinning.** The example pins `@main`, which is convenient for everyday repositories (fixes propagate without per-repo PRs) but means the check semantics can change under a PR. Repositories that need reproducibility — for example a DHF repository preparing a regulatory submission — should pin to a release tag (e.g., `@v1`) once tags are cut, so a submission-gating PR is validated against a known-good state rather than whatever is on `main`.

The workflow enforces:

- Device-by-default lane selection from changed files, with non-device carve-outs declared in `.github/thorne-lanes.yml` on the base branch.
- A non-empty `## Summary` for non-device light-lane PRs.
- Required Thorne template sections are present.
- At least one Thorne Scope item is checked.
- `Not Thorne-related` is not combined with Thorne-specific scope items.
- DHF Trace text is non-placeholder when the PR touches device function, Multiple-Function impact assessment, pre-design scaffolding, or DHF/QMS artifacts.
- Device-function and Multiple-Function-impact PRs select at least one concrete
  Safety Class and identify every affected device software item as
  `ARC-NN — Class A/B/C`.
- Every selected class maps to an affected item, and every affected item's
  class is selected. The mapping is read from `## Affected Device Software
  Items` when that heading is present, and from the DHF Trace only when it is
  absent, so trace prose that merely mentions an item is not read as a
  declaration.
- On any Thorne-scoped PR: `C-adjacent` is rejected as a class, Safety Class
  `N/A` is not combined with a concrete class, and `TBD / blocked until
  resolved` is not left checked.
- Thorne-related PRs confirm the required boundary checklist items.

### Thorne PR Verification-Traceability Check

`.github/actions/thorne-pr-verification-trace` runs the read-only `vvtrace`
engine against a device source repository's pull request, enforcing the
machine-checkable trace conventions against the controlled DHF (thorne-dhf#113
AC3): `@verifies SRS-NN-MM` tags and `implements: SDD-NN` declarations must cite
DHF ids that exist and be well-formed. It emits the read-only evidence and
module manifests as a build artifact and fails CI on any finding; it never
writes the DHF or the TRM.

To use it in a repository, add this workflow. The `ref:` on the checkout is
required: the action records the commit it actually scanned, read from the tree,
and fails if that is not the event's head commit — so a default checkout, which
gives the synthetic merge ref, is rejected rather than silently producing
evidence for a tree nobody reviewed.

```yaml
name: Thorne Verification Traceability

on:
  pull_request:

permissions:
  contents: read

jobs:
  thorne-pr-verification-trace:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - uses: eiro-inc/.github/.github/actions/thorne-pr-verification-trace@main
        with:
          token: ${{ secrets.DHF_READ_TOKEN }}
```

The action installs the pinned engine (`vvtrace-ref`, defaulting to the commit
tagged `v0.1.0`) and needs `token` with read access to `eiro-inc/thorne-dhf`
(and, while private, `eiro-inc/thorne-vv-tooling`). It fetches the DHF into
`$RUNNER_TEMP`, outside the workspace, so the DHF is never part of the scanned
tree. After adding the workflow, require the
`thorne-pr-verification-trace` status check before merge. See the action's
[README](.github/actions/thorne-pr-verification-trace/README.md) for inputs.

## Issue Templates

The issue templates currently focus on Thorne traceability:

- Thorne device implementation.
- Thorne DHF artifact.
- Thorne non-device product work.
- Thorne pre-design scaffolding.
