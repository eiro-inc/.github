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
The Action installs the **pinned** engine at a release commit SHA.

The manifests record the commit the Action **actually scanned**, read from the
tree rather than from the event payload. If that commit is not the event's head
commit — the default `actions/checkout` on `pull_request` gives you the synthetic
merge ref — the Action **fails** rather than recording provenance for a tree it
did not scan. Check out the head commit as shown below.

The controlled DHF is fetched into `$RUNNER_TEMP`, deliberately **outside**
`$GITHUB_WORKSPACE`: `vvtrace` scans `src` recursively, so a DHF checkout inside
the scanned tree would let DHF-resident source files be harvested and attributed
to the repository under review.

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
          token: ${{ secrets.DHF_READ_TOKEN }}
```

The `ref:` on the checkout is **required, not advisory** — without it the Action
fails the mismatch check described above.

## Provisioning

`token` — read access to `eiro-inc/thorne-dhf` (SRS/SDD/IFS/HAZ) and, while the
engine repo is private, to `eiro-inc/thorne-vv-tooling` for the `pip install`.
Use a GitHub App installation token or a fine-grained PAT stored as an Actions
secret. The token is used only for the DHF fetch and the engine install, and is
held solely in git's in-memory credential cache for that one step: it is never
written to disk, never reaches the pip command line or the logs, and the cache
daemon is torn down when the step exits, so it is not retrievable by later steps
in the job. The step's git config is scoped to a throwaway `GIT_CONFIG_GLOBAL`,
so the runner's own gitconfig is left untouched.

## Inputs

| Input | Default | Meaning |
|---|---|---|
| `src` | `.` | Path to the checked-out source to scan. |
| `dhf-repo` | `eiro-inc/thorne-dhf` | Controlled DHF source. |
| `dhf-ref` | `main` | DHF ref or commit SHA to validate against. |
| `vvtrace-ref` | `6dcf5389…` (`v0.1.0`) | Engine **commit SHA** to install. Pin a SHA, not a tag: the engine repo has no tag protection, so a tag can move. |
| `artifact-name` | `vvtrace-manifests` | Manifest artifact name; override if the action runs twice in one job. |
| `token` | — (required) | Read token for the DHF and the engine repo. |

## Scope

This delivers thorne-dhf#113 **AC3** — the `@verifies` parser/checker that
validates cited SRS ids exist and emits the machine-readable manifest.
**AC2** (the device-PR checker validating that the SRS/SDD/IFS/HAZ ids cited in
the *PR body's* DHF Trace section actually exist) is a separate change to the
`thorne-pr-boundary-check` Action, tracked in eiro-inc/.github#23.
