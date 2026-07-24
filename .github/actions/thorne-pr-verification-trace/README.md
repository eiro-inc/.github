# Thorne PR Verification-Traceability Check

Composite action that runs the read-only `vvtrace` engine against a device
source repository's pull request, enforcing the machine-checkable trace
conventions against the controlled DHF (ADR-0008; #113 AC1-2 — the
`@verifies`/SRS-ID lint):

- `@verifies SRS-NN-MM` tags cite requirements that **exist** in the SRS and are
  well-formed (`vvtrace lint`);
- `implements: SDD-NN` declarations cite SDD components that **exist**
  (`vvtrace implements`).

It validates only — it never writes the DHF or the TRM (ADR-0005 §7). A finding
fails the job; the *gate* is the caller's branch protection marking the check
required.

Enforcement lives here (`eiro-inc/.github`), not in the engine repo, so a device
repo's CI is not coupled to the validated-engine repo (ADR-0008 §Decision 2).
The Action installs the **pinned** engine at a released tag.

## Usage (in a device source repo)

```yaml
name: traceability
on:
  pull_request:

jobs:
  vvtrace:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      # Check out the head commit so the scanned tree matches what the PR
      # proposes (not the synthetic merge ref).
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - uses: eiro-inc/.github/.github/actions/thorne-pr-verification-trace@main
        with:
          # src: .            # subtree to scan, if not the whole repo
          # vvtrace-ref: v0.1.0
          token: ${{ secrets.DHF_READ_TOKEN }}
```

## Provisioning

`token` — read access to `eiro-inc/thorne-dhf` (SRS/SDD/IFS/HAZ) and, while the
engine repo is private, to `eiro-inc/thorne-vv-tooling` for the `pip install`.
Use a GitHub App installation token or a fine-grained PAT stored as an Actions
secret. The token is used only for the DHF checkout and the engine install; it
is not persisted (`persist-credentials: false`) and is kept off the pip command
line and out of the logs.

## Inputs

| Input | Default | Meaning |
|---|---|---|
| `src` | `.` | Path to the checked-out source to scan. |
| `dhf-repo` | `eiro-inc/thorne-dhf` | Controlled DHF source. |
| `dhf-ref` | `main` | DHF ref to validate against. |
| `vvtrace-ref` | `v0.1.0` | Engine tag to install (pin; do not float to a branch). |
| `token` | — (required) | Read token for the DHF and the engine repo. |

## Scope

This is the `@verifies`/SRS-ID *source* lint half of #113 AC1-2. Upgrading the
PR-body DHF-Trace check from anchor *shape* to anchor *existence* (in the
`thorne-pr-boundary-check` Action) is tracked separately.
