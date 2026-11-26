# layout

GDS, the tape-out runners and the precheck evidence. Nothing here runs a heavy
job on the host you type on: `build.sh` and `precheck/run.sh` submit the work to
the Spot batch fleet and bring the evidence back.

| Path | What it is |
|---|---|
| `toolchain.json` | The pins: the wafer.space template, precheck and PDK commits, the Nix installer, the slot's die, and the `klt` commands the runners call. Its `_comment` is append-only: a new pin is a new paragraph. |
| `toolchain_pin.py` | The one pin check that every runner and the CI test share. |
| `build.sh` | The pinned template -> `chip_top.gds`, on Spot. |
| `precheck/run.sh` | One GDS -> the wafer.space precheck, on Spot. |
| `jobs/` | What the Spot instance runs. `nix-env.sh` is the bootstrap both jobs share. |
| `spot.py`, `records.py` | The submit / collect / record driver and the record format. |
| `build/records/`, `precheck/records/` | Evidence records, append-only. |
| `die.json` | The die `main` holds: its GDS by sha256 and the records behind it. |
| `artifacts.json` | Every GDS this repo has stored, by sha256. |
| `_work/` | Scratch, never committed: staged tarballs and collected job outputs. |

## Run a job

```
layout/build.sh check
layout/build.sh submit [--group ID] [--probe] [--timeout SECONDS] [--on-demand] [--dry-run]
layout/build.sh collect GROUP [--wait SECONDS]
layout/build.sh record layout/_work/runs/GROUP/s00 --as-die
```

`precheck/run.sh` takes the same four steps, with
`submit --gds FILE --label NAME [--cob] [--id HEX8] [--threads N] [--workers N]`
and `record ... --is-die`.

- `check` validates `toolchain.json` and looks every pinned `klt` command up in
  `klt --help`. A missing command is exit 1, naming the command and the
  `uv tool install` that fixes it. Every runner runs it before anything else.
- `submit` refuses a tree with uncommitted `layout/` changes, because the job
  runs the committed tree. It archives `layout/` at HEAD, adds the upstream
  repos at their pinned commits under `layout/vendor/` (`git archive` of the
  commit, so git verifies it and the job clones nothing), and for a precheck
  the GDS under test. `--dry-run` stages the tarball and touches no AWS.
- `collect` pulls the shard's outputs into `layout/_work/runs/GROUP/s00/`.
- `record` verifies what came back and writes one record, or refuses to.

`submit` always passes `--wait-for-capacity 600`, as the worker host rules
require: a full Spot budget is waited out, not failed.

A shard Spot reclaims is `interrupted`; the fleet captain's reconcile pass,
which runs every two hours, relaunches it from scratch, and `collect` keeps
polling through that. To not wait, run the same `submit` again with the same
`--group`: the job id keeps its launch ledger, so the record's
`retry_count` still counts the lost attempt. A job that was reclaimed on
Spot, or that cannot be sharded to fit between reclaims, takes
`submit --on-demand`: the fleet's ruling for on-demand capacity, same cap,
billed at the on-demand rate. It needs a submit identity allowed to launch
on-demand; the loom-worker role is refused by IAM (`UnauthorizedOperation`
on `ec2:RunInstances`, 2026-11-26; 2AMLogic/2am#7963 tracks the unapplied
policy), so from a worker that submit stages the job and launches nothing.

## What the job does

Both jobs run as `repo-script` shards on the batch fleet's heavy image. Each
one bootstraps the same toolchain wafer.space's own CI and Docker image use:

1. installs Nix at the sha256-pinned release in `toolchain.json`;
2. runs `make clone-pdk` in the upstream tree, so Ciel delivers gf180mcuD at
   the open_pdks commit that tree's Makefile pins;
3. refuses to continue unless `$PDK_ROOT/gf180mcuD/SOURCES` names that commit;
4. records the tool versions of the upstream flake's dev shell (`tools.json`);
5. runs the flow.

The build runs the template's own `librelane-condensed` target with the
Makefile variables pinned in `toolchain.json`. The precheck runs
`precheck.py --top chip_top --slot 1x1` from the pinned precheck tree; its exit
code is the verdict. `--probe` stops a build after step 4, to prove the
environment in minutes before spending the flow's time on it.

The fleet's PDK store is deliberately not used. It carries another open_pdks
revision, and the DRC decks the precheck runs ship inside the PDK.

## Records

A record is a directory `layout/<stage>/records/<UTC stamp>-<commit>-<label>/`
holding `record.json`, the same record rendered as `record.md`, and the
evidence files it names, each by sha256. Three rules:

- **Written once.** The directory is created exclusively and cannot be
  rewritten. A later run is a new record; nothing edits or deletes an old one.
- **Three statuses.** `pass`, `fail` (the job ran and the check did not pass)
  and `error` (the job did not get far enough to say). A `fail` is recorded
  too: it is evidence.
- **Checked.** `verification/test_layout_toolchain.py` re-hashes every
  committed record's evidence and fails on a changed, missing or unlisted file.

`*.log` is ignored repo-wide; the `.gitignore` lets the logs beside a record
through, as `sim/` does for its corner logs.

## The GDS

A full-slot GDS is about 178 MB, past git's hard limit, and this repo uses no
LFS. The bytes go to the fleet artifact store and git keeps the name:

```
klt artifact get layout/artifacts.json#<entry name> -o chip_top.gds
klt artifact verify layout/artifacts.json
```

`get` writes only bytes that re-hash to the entry's sha256, and does not
create parent directories. `verify` asks the store for every entry's size and
sha256. `--local` re-hashes files at their entry names under the repo root
instead, so it needs them fetched there first: in a clean checkout no entry
resolves to a file and it exits 1.

`layout/die.json` names the die `main` currently holds, by sha256, with the
build record that produced it and the precheck record that cleared it.

## Keeping `main` precheck-clean

Every integration repeats four steps and commits what they produce:

```
layout/build.sh submit && layout/build.sh collect GROUP
layout/build.sh record layout/_work/runs/GROUP/s00 --as-die
layout/precheck/run.sh submit --gds layout/_work/runs/GROUP/s00/files/build/out/chip_top.gds --label die
layout/precheck/run.sh collect GROUP && layout/precheck/run.sh record .../s00 --is-die
```

`record --as-die` moves `die.json` to the new GDS and drops its precheck
record, so between a build and its precheck `main` names a die that is not
cleared. CI fails on exactly that: `npm test` requires the GDS in `die.json`
to have a passing precheck record with the same sha256, and to be in
`artifacts.json`. Do both in one PR.

A pin bump needs a new precheck record in the same PR. `npm test` also
requires the die's precheck record to name the `wafer_space.precheck.commit`
and `wafer_space.pdk.open_pdks_commit` that `toolchain.json` pins: a verdict
belongs to the precheck tree and the PDK it ran, and a moved pin leaves the
GDS, so its sha256, unchanged. Commit the bump first (`submit` runs the
committed tree), fetch the die's GDS, and run the precheck's `submit` and
`record --is-die` on it. The template and `klt` pins are not held to this;
neither can change a verdict already recorded.

A bump of the template or precheck commit also needs the two sha literals in
`PinFileTests.test_committed_pins_validate`
(`verification/test_layout_toolchain.py`) updated in the same PR, or that test
fails even when the record is current. This holds for a template-only bump too,
whatever the precheck record says. The literals are deliberate: a pin moving
has to show up as a reviewed change in the test, not only in `toolchain.json`.
