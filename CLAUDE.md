# gf180-cryo-char — agent instructions

Open-source canary block: a Device characterization test chip on the gf180mcu PDK,
designed and verified by AI agents — a **mixed-signal** block.

- **PDK**: gf180mcu (open PDK).
  Digital: cocotb + Icarus, Yosys, OpenROAD. Analog: xschem + ngspice.
  Layout, DRC, and LVS go through klayout-tools (`klt`).
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker is
  scoped to the tool, so keep design-specific detail (spec values, this repo's
  content) out of it and describe the gap, not the design.
- **Verification is the product**: no claim without a testbench. Recorded
  results are append-only evidence; a result is not superseded by deletion, it
  is superseded by a later record that says why.
- Spec changes go through `spec/` with a decision record. Agents do not relax
  the ratified spec to make a result pass.
- **Ratification is a merged PR, and the status line merges with it.**
  Open the record's PR with `Status: proposed`. When ready, set
  `Status: RATIFIED` or mark only the ratified rows for a partial ratification.
  Push the status change in the ratifying PR before requesting any review.
  A change to a spec row or bound needs an EE review and a market review; a
  process record (no spec row or bound) needs only the EE review, and a record
  whose classification is unclear gets both. The reviewers must be distinct,
  and neither may have authored the PR or the design. They follow
  centrally pinned instructions and record their reviews against that head.
  Once the operator ratifies and `2am/ratification` turns green, merge that
  head. If you push again, repeat the reviews that apply on the new head
  before the operator ratifies it. Keep reviewer files out of this repo.

- **Port the spec, not the GDS.** The upstream repo has only finished GDS.
  Generate every structure from NIST's published spec with gLayout or the
  gf180mcuD PDK cells, and record the NIST structure ID it maps to. Never
  trace, flatten or convert the SKY130 layout. A structure with no gf180
  counterpart is recorded as dropped, with the reason; it is never invented.
- **The tape-out date beats coverage.** GDS is due 2026-12-16 and must pass
  `gf180mcu-precheck`. Integrate the structures that are clean, keep the die
  precheck-clean at every merge, and cut a structure rather than slip the date
  or waive a rule.

## Harness bootstrap

Copy the layout and DRC half from `gf180-antifuse`, which is also a gf180
characterization array aimed at wafer.space Run 3. Copy the analog sim half
(ngspice, gf180 corners) from `gf180-comparator`. The top-level die, padring
and precheck come from `wafer-space/gf180mcu-project-template`; do not build a
second padring.

<!-- BEGIN LOOM ORCHESTRATION -->
This repository uses [Loom](https://github.com/2AMLogic/loom) for AI-powered development orchestration — see the Loom repository for the full guide (roles, labels, worktrees, configuration). When installed, Loom also writes a locally-substituted copy of that guide to `.loom/CLAUDE.md`.

Work is coordinated through `loom:` labels on issues and pull requests, and the same roles run either under `loom-daemon` or by hand in an attended session — daemon mode is optional. Create the labels once with `.loom/scripts/sync-labels.sh` (an install ships `.github/labels.yml` but does not create the labels on the forge). A pull request ready for review carries `loom:review-requested`; Judge reviews it and applies `loom:pr` (approved) or `loom:changes-requested`; Doctor fixes a `loom:changes-requested` pull request and returns it to `loom:review-requested`. Only a `loom:pr` pull request gets merged, and always via this repo's merge script (`.loom/scripts/merge-pr.sh`) — never a raw forge merge command such as `gh pr merge`. Full state machine: `.loom/docs/label-state-machine.md`.
<!-- END LOOM ORCHESTRATION -->
