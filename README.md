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

## Reusable Workflows

### Thorne PR Boundary Check

`.github/workflows/thorne-pr-boundary-check.yml` validates that a pull request using the organization template has completed the Thorne-specific sections. The first version checks PR-body declarations only; repository-specific static import-boundary checks remain local to each source-code repository.

To use it in a repository, add this caller workflow:

```yaml
name: Thorne PR Boundary Check

on:
  pull_request:
    types: [opened, edited, synchronize, reopened, ready_for_review]

jobs:
  thorne-pr-boundary-check:
    uses: eiro-inc/.github/.github/workflows/thorne-pr-boundary-check.yml@main
```

After adding the caller workflow, configure the repository's branch protection or organization ruleset to require the `Validate Thorne PR boundary declarations` status check before merge.

The workflow enforces:

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
