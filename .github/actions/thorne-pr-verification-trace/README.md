# Thorne PR Verification-Traceability Check

Composite action that runs the read-only `vvtrace` engine against a device
source repository's pull request, enforcing the machine-checkable trace
conventions against the controlled DHF (ADR-0008; thorne-dhf#113 **AC3** — the
`@verifies` parser/checker):

- `@verifies SRS-NN-MM` tags cite requirements that **exist** in the SRS and are
  well-formed (`vvtrace harvest`);
- `implements: SDD-NN` declarations cite SDD components that **exist**
  (`vvtrace implements`).

It validates and **emits AC3's machine-readable manifests** — an evidence
manifest (`@verifies`) and a module manifest (`implements:`) — uploaded as the
`vvtrace-manifests` build artifact. It never writes the DHF or the TRM (the
manifests are read-only evidence, ADR-0005 §7). A finding fails the job; the
*gate* is the caller's branch protection marking the check required.

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

This delivers thorne-dhf#113 **AC3** — the `@verifies` parser/checker that
validates cited SRS ids exist and emits the machine-readable manifest.
**AC2** (the device-PR checker validating that the SRS/SDD/IFS/HAZ ids cited in
the *PR body's* DHF Trace section actually exist) is a separate change to the
`thorne-pr-boundary-check` Action, tracked in eiro-inc/.github#23.
