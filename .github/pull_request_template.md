## Summary

<!-- What changed and why. This is all a non-device PR needs. -->

## Related Issue

<!-- Link the repository issue (e.g. Closes #123), or write N/A. -->

<!--
──────────────────────────────────────────────────────────────────────────
DEVICE-LANE SECTION ↓  — only required if this PR touches device code.

The `thorne-pr-boundary-check` decides the lane automatically from the files
you changed: everything is device unless carved out in `.github/thorne-lanes.yml`.

• Non-device PR? Leave the block below as-is (or delete it) and you're done.
• Device PR? The check fails until the block is filled in — and it lists the
  exact files that put you on the device lane.
──────────────────────────────────────────────────────────────────────────
-->

<details>
<summary><b>Device-lane details</b> — fill in only for device-code changes</summary>

## Thorne Scope

- [ ] Device function
- [ ] Non-device function
- [ ] Multiple-Function impact assessment
- [ ] Pre-design scaffolding under CMP §7
- [ ] DHF/QMS artifact
- [ ] Not Thorne-related

## DHF Trace

<!-- Cite controlling anchors: CMP §7, DDS §5/§6/§7, UNS, SRS, SDD, HAZ, TRM, DR, etc. -->

## Safety Class

- [ ] Class A
- [ ] Class B
- [ ] Class C
- [ ] C-adjacent integrity control
- [ ] N/A
- [ ] TBD / blocked until resolved

## New Dependencies

<!-- Required whenever this PR changes a dependency manifest or lockfile
     (package.json / lockfiles, Cargo.toml/.lock, gradle files, Package.swift/.resolved).
     One line per NEW or UPGRADED dependency:
       name@version — runtime|dev — device path? — purpose — license — maintenance note
     If the manifest change introduces no new/upgraded dependency, say why:
       "None — lockfile refresh only, no dependency changes."
     Internal @eiro/* packages count. (CMP §10) -->

- None

## Verification

<!-- State what was checked and where evidence lives. -->

- [ ] Build/typecheck
- [ ] Unit tests
- [ ] Integration tests
- [ ] Static analysis / lint
- [ ] Dependency or SBOM impact reviewed
- [ ] Secret scan / cybersecurity impact reviewed
- [ ] DHF document review only
- [ ] Other:

## Thorne Boundary Check

- [ ] This PR does not introduce Eiro-authored clinical interpretation.
- [ ] This PR does not introduce safety detection, safety flagging, triage, crisis prediction, priority ranking, patient-status assignment, or treatment recommendation.
- [ ] This PR does not introduce PHQ-9 item 9 default alerting, urgent notification, 24-hour, push, or on-call alert behavior.
- [ ] This PR does not change the meaning, priority, salience, or safety significance of device output from a non-device surface.
- [ ] If this is pre-design scaffolding, it stays within CMP §7 and does not implement clinical device behavior.

## Reviewer Notes

<!-- Call out risk, traceability gaps, follow-up DHF updates, or known limitations. -->

</details>
