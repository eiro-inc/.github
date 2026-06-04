# GitHub Templates for Eiro Inc. QMS

This repository provides organization-default GitHub templates and reusable workflows for Eiro Inc. repositories.

## Thorne Pull Request Template

The organization-level pull request template includes Thorne-specific sections for:

- Thorne scope classification.
- DHF trace anchors.
- Safety class declaration.
- Verification evidence.
- Boundary confirmations for the device/non-device membrane.

Repositories inherit this template unless they define a repository-local `.github/pull_request_template.md`.

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

**Pinning.** The example pins `@main`, which is convenient for everyday repositories (fixes propagate without per-repo PRs) but means the check semantics can change under a PR. Repositories that need reproducibility — for example a DHF repository preparing a regulatory submission — should pin to a release tag (e.g., `@v1`) once tags are cut, so a submission-gating PR is validated against a known-good state rather than whatever is on `main`.

The workflow enforces:

- Device-by-default lane selection from changed files, with non-device carve-outs declared in `.github/thorne-lanes.yml` on the base branch.
- A non-empty `## Summary` for non-device light-lane PRs.
- Required Thorne template sections are present.
- At least one Thorne Scope item is checked.
- `Not Thorne-related` is not combined with Thorne-specific scope items.
- DHF Trace text is non-placeholder when the PR touches device function, Multiple-Function impact assessment, pre-design scaffolding, or DHF/QMS artifacts.
- Device-function PRs select at least one Safety Class item other than `N/A`.
- Thorne-related PRs confirm the required boundary checklist items.

## Issue Templates

The issue templates currently focus on Thorne traceability:

- Thorne device implementation.
- Thorne DHF artifact.
- Thorne non-device product work.
- Thorne pre-design scaffolding.
