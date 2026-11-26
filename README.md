# gf180-cryo-char

A Device characterization test chip on the [gf180mcu](https://github.com/google/gf180mcu-pdk) open PDK,
designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the open-source
flow — cocotb + Icarus and Yosys/OpenROAD on the digital side, xschem + ngspice
on the analog side.

It is a device-characterization test chip: arrays of single transistors,
ring oscillators and passive structures, with on-chip multiplexing so each one
can be measured from the pads. It is a gf180mcuD port of the SKY130 MPW-5 test
tile designed at NIST and the University of Michigan
([openfasoc_cryo_caravel](https://github.com/msaligane/openfasoc_cryo_caravel),
Apache-2.0). The structures are regenerated from NIST's published spec for each
one ([NIST MPW-5 dataset](https://data.nist.gov/od/id/mds2-2997)) with the
[gLayout](https://github.com/ReaLLMASIC/gLayout) generators, so measurements of
the two chips can be compared structure by structure. The target is a full
[wafer.space](https://wafer.space) Run 3 slot (3.932 × 5.122 mm,
gf180mcuD), and the work was requested by a member of the wafer.space community.

## Status

```
Area (measured, post-layout): not yet measured
Design stage: spec
```

<!-- The two fields above are correct as they stand for a repo where nothing is
     built yet, so there is nothing to fill in here — only to keep current. They
     are a fixed-location summary a chip-level integrator reads without parsing
     the prose below, so the keys, their spelling, and their order do not change.

     Area (measured, post-layout): the as-built area of a DRC-clean,
     LVS-matched layout, as a number with units (e.g. 1.059 mm²), taken from
     this repo's own committed measurement. Never a target, a plan, or an
     estimate — the ratified bound is the AREA row of the target-specification
     table below. Until a layout exists, the literal "not yet measured".

     Design stage: exactly one token, from this ladder, in order —
     spec | schematic-sim | layout-DRC-LVS-clean | extracted-verified | silicon
     — describing what this repo has produced and recorded evidence for, never
     what it is aiming at. One token; not a range, not a hedge, not prose. -->

**Just opened, specification phase.** Nothing is designed yet, nothing has been
taped out, and nothing has been measured.

The [T1 signoff report](signoff/block-manifest.signoff.json) grades the analog
measurement circuits and digital selection logic separately. Run this check
from the repo root to reproduce the committed report.

```sh
uvx --from "$(cat signoff/klt-pin.txt)" klt signoff \
  --manifest signoff/block-manifest.json --check signoff/block-manifest.signoff.json
```

The check exits zero when the report matches. Its `tier`, `t1_met_count`
and per-item verdicts show how much design evidence has passed.

Run the same harness and evidence checks as CI from the repo root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r signoff/klt-pin.txt
npm run check:ci
```

Use Python 3.12 and npm. The harness tests generate pass, fail, and incomplete
records in a temporary directory, then load any committed testbench manifests.
The remaining checks reproduce the repo-hygiene attestation and the signoff
report. These checks run without a PDK install.

**Not being built:**
- **Copied layout.** The upstream repo ships only finished GDS, with no
  generator scripts. Every structure here is regenerated from NIST's spec
  for that structure, never traced from the SKY130 GDS.
- **Cryogenic qualification.** The original chip was measured at cryogenic
  temperatures. This repo targets room-temperature models; cryogenic behaviour
  is for whoever measures the silicon.
- **Packaging, bring-up board and test firmware.** These wait on silicon.

**The hard date:** GDS that passes the
[wafer.space precheck](https://github.com/wafer-space/gf180mcu-precheck) by
**2026-12-16**, built on the
[project template](https://github.com/wafer-space/gf180mcu-project-template).
A structure that is not DRC/LVS clean by then is left off the die, not
waived.

## Built agent-native

Every specification, decision record, testbench, and line of documentation in
this repo is produced by AI agents working from a ratified spec and an
append-only evidence trail — not human-authored work that agents merely
assisted with. Verification is the product: every claim traces to a recorded
result. Where the agents hit friction with the open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction gets
filed as a public issue against the tool itself, so the fix benefits everyone
using gf180mcu, not just this repo.

## Target specification (DRAFT — engineering to ratify, see issue #1)

| Parameter | Target | Stretch |
|---|---|---|
| Die | full wafer.space Run 3 slot, 3.932 × 5.122 mm, gf180mcuD | — |
| Structure coverage | every structure in the NIST MPW-5 test-tile spec that has a gf180mcuD counterpart, mapped one-to-one in `spec/` | added gf180-only devices (5 V / 6 V transistors) |
| Signoff | wafer.space gf180mcu-precheck passes on the submitted GDS | — |
| Selection | every structure reachable from the pads through on-chip multiplexing; mux leakage below the smallest current measured on that structure | — |
| GDS delivery | on or before 2026-12-16 | 2026-12-09 |

Issue #1 takes this target spec through review. A separate EE reviewer and a
separate market reviewer, neither the author of the PR or of the design, read centrally pinned
instructions and record their reviews against the PR's current head; the
operator then ratifies, and the `2am/ratification` status turns green. The
review instructions are not stored in this repo, and a new push to the PR
starts the reviews over.

## Repo layout

```
design/        schematics (xschem)
flow/          synthesis + place-and-route (Yosys, OpenROAD)
layout/        GDS + DRC/LVS reports (klayout-tools driven)
measurements/  silicon characterization (empty until tape-out)
rtl/           Verilog sources
sim/           analog testbenches + PVT corner results
spec/          ratified spec + decision records
verification/  cocotb testbenches
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
