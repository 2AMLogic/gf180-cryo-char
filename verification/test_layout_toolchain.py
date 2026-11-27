"""layout/ pin, evidence-record, shard-recording and die-consistency checks
(issue #4)."""

import contextlib
import datetime as dt
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from layout import records, spot, toolchain_pin

REPO = Path(__file__).resolve().parents[1]
LAYOUT = REPO / "layout"

PRECHECK_COMMIT = ("wafer_space", "precheck", "commit")
OPEN_PDKS_COMMIT = ("wafer_space", "pdk", "open_pdks_commit")

KLT_HELP = """usage: klt [-h] [--version] <command> ...

Tools for AI agents to work with IC layout.

positional arguments:
  <command>
    stats               report area, density, and polygon/vertex counts of a
                        GDSII/OASIS stream
    drc                 run a headless DRC deck against a GDSII/OASIS stream
    functional-verification
                        run a cocotb regression against Icarus/Verilator
    cells               report the cell hierarchy of a GDSII/OASIS stream
    diff                compare two GDSII/OASIS streams for equal geometry,
                        labels and hierarchy
    artifact            put/get/verify/delete evidence bytes in the fleet
                        artifact store by sha256, with a committed manifest

options:
  -h, --help            show this help message and exit
"""


class PinFileTests(unittest.TestCase):
    def test_committed_pins_validate(self):
        pins = toolchain_pin.load(LAYOUT)
        self.assertEqual(pins["klt_required_commands"][0], "drc")
        upstream = pins["wafer_space"]
        self.assertEqual(
            upstream["template"]["commit"], "d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c"
        )
        self.assertEqual(
            upstream["precheck"]["commit"], "9b4e7dab6af073d02b81ecc368069540d2f67db9"
        )
        self.assertEqual(pins["die"]["width_um"], 3932)
        self.assertEqual(pins["die"]["height_um"], 5122)

    def test_klt_pin_is_self_consistent(self):
        pins = toolchain_pin.load(LAYOUT)
        self.assertTrue(
            pins["klt_install"].endswith("@" + pins["klt_last_verified_commit"])
        )

    def test_load_drops_the_underscore_commentary(self):
        raw = json.loads((LAYOUT / "toolchain.json").read_text())
        self.assertTrue(any(k.startswith("_") for k in raw), "no _ key to strip")
        self.assertEqual(
            [k for k in toolchain_pin.load(LAYOUT) if k.startswith("_")], []
        )

    def _invalid(self, pins):
        if not isinstance(pins, str):
            pins = json.dumps(pins)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "toolchain.json"
            path.write_text(pins)
            with self.assertRaises(toolchain_pin.PinError) as caught:
                toolchain_pin.load(path.parent)
        return str(caught.exception)

    def _pins(self, **changes):
        return {**toolchain_pin.load(LAYOUT), **changes}

    def test_duplicate_key_is_rejected(self):
        message = self._invalid('{"klt_install": "a", "klt_install": "b"}')
        self.assertIn("duplicate", message)
        self.assertIn("klt_install", message)

    def test_unknown_key_is_rejected(self):
        self.assertIn(
            "klt_required_command", self._invalid({"klt_required_command": ["drc"]})
        )

    def test_missing_key_is_rejected(self):
        self.assertIn("missing required key 'klt_install'", self._invalid({}))

    def test_short_commit_is_rejected(self):
        message = self._invalid(self._pins(klt_last_verified_commit="046ba74"))
        self.assertIn("klt_last_verified_commit", message)

    def test_install_and_verified_commit_must_move_together(self):
        message = self._invalid(self._pins(klt_install="git+https://x/y@" + "0" * 40))
        self.assertIn("update both together", message)

    def test_missing_klt_command_is_named(self):
        pins = {"klt_required_commands": ["drc", "stats", "nope", "report", "cells"]}
        self.assertEqual(
            toolchain_pin.missing_klt_commands(pins, KLT_HELP), ["nope", "report"]
        )
        listed = toolchain_pin.klt_subcommands(KLT_HELP)
        self.assertIn("functional-verification", listed)
        self.assertNotIn("run", listed)

    def test_check_fails_loudly_on_a_missing_pinned_command(self):
        trimmed = KLT_HELP.replace(
            "    artifact            ", "    zrtifact            "
        )
        err = io.StringIO()
        rc = toolchain_pin.main(["--check"], help_text=trimmed, stderr=err)
        self.assertEqual(rc, 1)
        self.assertIn("'artifact'", err.getvalue())
        self.assertIn(
            "uv tool install " + toolchain_pin.load(LAYOUT)["klt_install"],
            err.getvalue(),
        )

    def test_check_passes_when_every_pinned_command_is_listed(self):
        out = io.StringIO()
        self.assertEqual(
            toolchain_pin.main(["--check"], help_text=KLT_HELP, stdout=out), 0
        )
        self.assertIn("toolchain.json: OK", out.getvalue())


class RecordTests(unittest.TestCase):
    def test_record_id_rejects_an_unsafe_label(self):
        when = dt.datetime(2026, 11, 26, 9, 30, tzinfo=dt.UTC)
        self.assertEqual(
            records.record_id(when, "ab12cd3", "control"),
            "20261126-093000-ab12cd3-control",
        )
        with self.assertRaises(ValueError):
            records.record_id(when, "ab12cd3", "../control")

    def test_record_is_append_only_and_its_evidence_is_hashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            records_dir = Path(tmp)
            rid = records.record_id(
                dt.datetime(2026, 11, 26, 9, 30, tzinfo=dt.UTC),
                "ab12cd3",
                "control",
            )
            bundle = records.reserve(records_dir, rid)
            self.assertTrue((bundle / "INCOMPLETE").is_file())
            (bundle / "console.log").write_text("Precheck successfully completed.\n")
            record = {
                "schema": records.SCHEMA_PRECHECK,
                "record_id": rid,
                "status": "pass",
            }
            record["evidence"] = records.evidence(bundle)
            path = records.write_record(bundle, record)
            self.assertEqual(path, bundle / "record.md")
            self.assertFalse((bundle / "INCOMPLETE").exists())
            self.assertIn("**Status**: pass", path.read_text())
            with self.assertRaises(records.RecordExists):
                records.write_record(bundle, record)
            self.assertEqual(records.check_intact(bundle), [])
            (bundle / "console.log").write_text("edited after the fact")
            self.assertTrue(records.check_intact(bundle))


def _pin(pins: dict, path: tuple) -> object:
    at = pins
    for key in path:
        at = at[key]
    return at


def _set_pin(pins: dict, path: tuple, value) -> None:
    at = pins
    for key in path[:-1]:
        at = at[key]
    at[path[-1]] = value


class CommittedLayoutTests(unittest.TestCase):
    def test_every_committed_record_is_intact(self):
        found = 0
        for path in sorted(LAYOUT.glob("*/records/*/record.json")):
            found += 1
            with self.subTest(record=str(path.relative_to(REPO))):
                record = json.loads(path.read_text())
                self.assertIn(
                    record["status"], ("pass", "fail", "error"), record["status"]
                )
                self.assertEqual(records.check_intact(path.parent), [])
        self.assertGreater(found, 0, "no layout evidence records committed")

    def test_the_die_on_main_is_precheck_clean(self):
        self._assert_die_is_precheck_clean(LAYOUT)

    def _assert_die_is_precheck_clean(self, layout: Path) -> None:
        pointer = layout / "die.json"
        if not pointer.is_file():
            self.skipTest("no die recorded on this branch yet")
        die = json.loads(pointer.read_text())
        gds_sha = die["gds"]["sha256"]
        precheck = (
            layout / "precheck" / "records" / die["precheck_record"] / "record.json"
        )
        record = json.loads(precheck.read_text())
        self.assertEqual(record["status"], "pass")
        self.assertEqual(record["input"]["sha256"], gds_sha)
        build = json.loads(
            (
                layout / "build" / "records" / die["build_record"] / "record.json"
            ).read_text()
        )
        self.assertEqual(build["status"], "pass")
        self.assertEqual(build["gds"]["sha256"], gds_sha)
        stored = [
            e["sha256"]
            for e in json.loads((layout / "artifacts.json").read_text())["entries"]
        ]
        self.assertIn(
            gds_sha,
            stored,
            "the die's GDS is not retrievable from the artifact manifest",
        )
        moved = toolchain_pin.moved_precheck_pins(
            record.get("pins"), toolchain_pin.load(layout)
        )
        if moved:
            self.fail(
                f"layout/die.json names precheck record {die['precheck_record']}, "
                f"which does not vouch for the die under the pins "
                f"layout/toolchain.json holds now ({'; '.join(moved)}). Re-run the "
                "precheck on the die's GDS and commit the new record together with "
                "the pin bump, as layout/README.md (Keeping `main` precheck-clean) "
                "prescribes"
            )

    def _standing_copy(self, tmp) -> Path:
        """A temp copy of what the die gate reads, its record holding the pin
        file's precheck pins, so that nothing but a test's own change fails.

        A committed record is append-only, so the gate is proven on a copy.
        """
        copy = Path(tmp) / "layout"
        inputs = [
            LAYOUT / name for name in ("die.json", "toolchain.json", "artifacts.json")
        ]
        inputs += sorted(LAYOUT.glob("*/records/*/record.json"))
        for path in inputs:
            target = copy / path.relative_to(LAYOUT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        pins = toolchain_pin.load(copy)

        def agree(record):
            for path in toolchain_pin.PRECHECK_PINS:
                _set_pin(record["pins"], path, _pin(pins, path))

        self._rewrite(self._die_record(copy), agree)
        return copy

    @staticmethod
    def _rewrite(path: Path, change) -> None:
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data, indent=2) + "\n")

    @staticmethod
    def _bumped(sha: str) -> str:
        return sha[:-1] + ("0" if sha[-1] != "0" else "1")

    def _die_record(self, layout: Path) -> Path:
        die = json.loads((layout / "die.json").read_text())
        return layout / "precheck" / "records" / die["precheck_record"] / "record.json"

    def test_exactly_the_precheck_and_pdk_pins_are_compared(self):
        self.assertEqual(
            toolchain_pin.PRECHECK_PINS, (PRECHECK_COMMIT, OPEN_PDKS_COMMIT)
        )

    def test_the_gate_rejects_a_die_prechecked_under_a_moved_pin(self):
        for path in (PRECHECK_COMMIT, OPEN_PDKS_COMMIT):
            name = ".".join(path)
            other = next(
                ".".join(p) for p in (PRECHECK_COMMIT, OPEN_PDKS_COMMIT) if p != path
            )
            with self.subTest(pin=name), tempfile.TemporaryDirectory() as tmp:
                layout = self._standing_copy(tmp)

                def bump(pins):
                    _set_pin(pins, path, self._bumped(_pin(pins, path)))

                self._rewrite(layout / "toolchain.json", bump)
                with self.assertRaises(AssertionError) as caught:
                    self._assert_die_is_precheck_clean(layout)
                message = str(caught.exception)
                self.assertIn(f"{name} moved", message)
                self.assertIn(_pin(toolchain_pin.load(layout), path), message)
                self.assertNotIn(f"{other} moved", message)
                self.assertIn("Re-run the precheck", message)
                self.assertIn("commit the new record", message)
                self.assertIn("layout/README.md", message)

    def test_the_gate_rejects_a_record_that_does_not_name_its_pins(self):
        cases = {
            "no pins block": (
                lambda record: record.pop("pins"),
                (PRECHECK_COMMIT, OPEN_PDKS_COMMIT),
            ),
            "no pdk commit": (
                lambda record: record["pins"]["wafer_space"]["pdk"].pop(
                    "open_pdks_commit"
                ),
                (OPEN_PDKS_COMMIT,),
            ),
        }
        for what, (remove, unnamed) in cases.items():
            with self.subTest(missing=what), tempfile.TemporaryDirectory() as tmp:
                layout = self._standing_copy(tmp)
                self._rewrite(self._die_record(layout), remove)
                with self.assertRaises(AssertionError) as caught:
                    self._assert_die_is_precheck_clean(layout)
                message = str(caught.exception)
                self.assertIn("Re-run the precheck", message)
                for path in (PRECHECK_COMMIT, OPEN_PDKS_COMMIT):
                    self.assertEqual(
                        f"{'.'.join(path)}: the record does not name it" in message,
                        path in unnamed,
                    )

    def test_a_template_pin_bump_alone_does_not_fail_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            layout = self._standing_copy(tmp)
            path = ("wafer_space", "template", "commit")

            def bump(pins):
                _set_pin(pins, path, self._bumped(_pin(pins, path)))

            self._rewrite(layout / "toolchain.json", bump)
            self._assert_die_is_precheck_clean(layout)

    def test_a_pin_bump_lands_with_a_record_prechecked_under_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            layout = self._standing_copy(tmp)
            old = self._die_record(layout)
            new = old.parent.with_name("99999999-999999-fffffff0-die") / old.name

            def bump(pins):
                _set_pin(
                    pins, PRECHECK_COMMIT, self._bumped(_pin(pins, PRECHECK_COMMIT))
                )

            self._rewrite(layout / "toolchain.json", bump)
            with self.assertRaises(AssertionError):
                self._assert_die_is_precheck_clean(layout)

            record = json.loads(old.read_text())
            record["record_id"] = new.parent.name
            _set_pin(
                record["pins"],
                PRECHECK_COMMIT,
                _pin(toolchain_pin.load(layout), PRECHECK_COMMIT),
            )
            new.parent.mkdir()
            new.write_text(json.dumps(record, indent=2) + "\n")

            def repoint(die):
                die["precheck_record"] = new.parent.name

            self._rewrite(layout / "die.json", repoint)
            self._assert_die_is_precheck_clean(layout)


FIXTURES = REPO / "verification" / "fixtures"
SHARD_WHEN = dt.datetime(2026, 11, 26, 9, 30, tzinfo=dt.UTC)
SHARD_COMMIT = "ab12cd3" + "0" * 33
GDS_BYTES = b"stub chip_top.gds bytes\n"
GDS_SHA = hashlib.sha256(GDS_BYTES).hexdigest()
SHARD_PINS = {
    "die": {
        "top": "chip_top",
        "slot": "1x1",
        "width_um": 3932,
        "height_um": 5122,
        "dbu_um": 0.001,
    },
    "klt_install": "git+https://github.com/2AMLogic/klayout-tools@" + "0" * 40,
}
KLT_STATS = {
    "bbox_um": {
        "left": 0.0,
        "bottom": 0.0,
        "right": 3932.0,
        "top": 5122.0,
        "width": 3932.0,
        "height": 5122.0,
    },
    "top_cell": "chip_top",
    "dbu_um": 0.001,
    "geometry_digest": "sha256:" + "1" * 64,
}
RUN_DONE = {
    "exit_code": 0,
    "wall_seconds": 6533,
    "instance_type": "m6i.4xlarge",
    "image_id": "ami-08688417b66e0c74d",
    "retry_count": 0,
    "started_at": "2026-11-26T09:20:01Z",
}
STATUS_DONE = {"state": "done", "failure_reason": None}
STATUS_RECLAIMED = {"state": "interrupted", "failure_reason": "spot reclaim"}
BUILD_JOB = {
    "make": {
        "PAD": "gf180mcu_fd_io",
        "SCL": "gf180mcu_fd_sc_mcu7t5v0",
        "SLOT": "1x1",
        "SRAM": "gf180mcu_fd_ip_sram",
    },
    "target": "librelane-condensed",
    "tools": {"librelane": "3.1.0.dev3", "nix": "nix (Nix) 2.28.4"},
    "metrics": {"design__instance__count": 251807, "design__violations": 0},
    "pass": True,
}
PRECHECK_JOB = {
    "input": {"name": "die.gds", "sha256": GDS_SHA, "bytes": len(GDS_BYTES)},
    "options": {
        "cob": False,
        "id": "FFFFFFFF",
        "slot": "1x1",
        "threads": 2,
        "top": "chip_top",
        "workers": "8",
    },
    "tools": {"klayout": "KLayout 0.30.12", "nix": "nix (Nix) 2.28.4"},
    "pdk_open_pdks_observed": ["open_pdks " + "0" * 40],
    "metrics": {"klayout__drc_error__count": 0, "magic__drc_error__count": 0},
    "wall_seconds": {"precheck die.gds id=FFFFFFFF threads=2 workers=8 cob=0": 5117},
    "image": {"profile": "heavy", "schema": "eda-batch-image/1"},
    "run_tag": "RUN_2026-11-26_13-44-39",
    "pass": True,
}
COMMON_EVIDENCE = {
    "console.log",
    "tools.json",
    "phases.txt",
    "run.json",
    "status.json",
    "harness.log",
}
DEFAULT = object()


class ShardRecordTests(unittest.TestCase):
    """``layout.spot <stage> record`` on a synthetic collected shard.

    ``record()`` lays a shard out under ``<home>/runs/<group>/s00/`` the way
    ``collect`` does, freezes ``spot.now()``, stubs ``klt`` and points the
    driver's paths at the temporary home. It returns the exit code, the
    bundles written, the record, ``die.json``, the ``say()`` lines, the
    ``klt`` calls and stderr.
    """

    def setUp(self):
        self.cells = {"top_cell_count": 1}
        self.klt_calls: list[tuple] = []
        self.fresh_home()

    def fresh_home(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)

    def _klt(self, *args):
        self.klt_calls.append(args)
        if args[0] == "cells":
            return self.cells
        if args[0] == "stats":
            return KLT_STATS
        if args[:2] == ("artifact", "put"):
            return {
                "entries": [
                    {
                        "sha256": GDS_SHA,
                        "size": len(GDS_BYTES),
                        "kind": "evidence",
                        "producer": {
                            "tool": args[args.index("--producer-tool") + 1],
                            "version": "0.9.3.dev5655",
                            "loom.repo": "2AMLogic/gf180-cryo-char",
                            "commit": SHARD_COMMIT,
                        },
                        "uri": (
                            "artifact:evidence/2AMLogic__gf180-cryo-char/"
                            f"{GDS_SHA[:2]}/{GDS_SHA}"
                        ),
                        "name": args[args.index("--name") + 1],
                    }
                ]
            }
        raise AssertionError(f"unexpected klt call: {args}")

    def _run(self, argv, **_):
        """No test reaches a real ``klt``: one that ran ``artifact put`` would
        upload to the fleet's artifact store."""
        if argv[0] == "klt":
            return subprocess.CompletedProcess(
                argv, 0, stdout=json.dumps(self._klt(*argv[1:])) + "\n", stderr=""
            )
        raise AssertionError(f"unexpected subprocess: {argv}")

    @staticmethod
    def _json(path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n")

    def record(
        self,
        stage: str,
        *,
        group: str = "g",
        named_group: bool = True,
        when: dt.datetime = SHARD_WHEN,
        run: dict | None = None,
        found: bool = True,
        status: dict | None = None,
        job=DEFAULT,
        gds: bool = True,
        die: dict | None = None,
        options: tuple = (),
    ) -> types.SimpleNamespace:
        spec = spot.STAGES[stage]
        runs = self.home / "runs"
        shard = runs / group / "s00"
        out = shard / "files" / spec["output"]
        self.klt_calls = []
        out.mkdir(parents=True, exist_ok=True)
        self._json(
            shard / "run.json",
            {
                **RUN_DONE,
                "outputs": {"found": [spec["output"]] if found else [], "missing": []},
                **(run or {}),
            },
        )
        self._json(shard / "status.json", status or STATUS_DONE)
        (shard / "harness.log").write_text("stub harness log\n")
        (out / "console.log").write_text("stub console log\n")
        self._json(out / "tools.json", {"nix": "nix (Nix) 2.28.4"})
        (out / "phases.txt").write_text("01 bootstrap\n02 flow\n")
        if stage == "build":
            if job is not None:
                self._json(out / "build.json", BUILD_JOB if job is DEFAULT else job)
            if gds:
                (out / "chip_top.gds").write_bytes(GDS_BYTES)
            self._json(out / "metrics.json", {"design__violations": 0})
        else:
            if job is not None:
                self._json(
                    out / "precheck.json", PRECHECK_JOB if job is DEFAULT else job
                )
            self._json(out / "flow" / "01-klayout-drc" / "config.json", {"step": 1})
            self._json(
                out / "flow" / "01-klayout-drc" / "reports" / "drc.klayout.json",
                {"errors": 0},
            )
            (out / "flow-files.txt").write_text(
                "flow/01-klayout-drc/config.json\n"
                "flow/01-klayout-drc/reports/drc.klayout.json\n"
            )
        staged = {
            "stage": stage,
            "group": group,
            "commit": SHARD_COMMIT,
            "submitted_utc": "2026-11-26T09:00:00+00:00",
            "capacity": "spot",
            "tarball_sha256": "b" * 64,
            "tarball_bytes": 7,
            "pins": SHARD_PINS,
        }
        if stage == "precheck":
            staged["input"] = {
                "label": "die",
                "sha256": GDS_SHA,
                "bytes": len(GDS_BYTES),
            }
        self._json(runs / f"{group}.submit.json", staged)
        die_path = self.home / "layout" / "die.json"
        if die is not None:
            self._json(die_path, die)
        records_dir = self.home / "layout" / stage / "records"
        argv = [
            stage,
            "record",
            str(shard),
            *(["--group", group] if named_group else []),
            *options,
        ]
        said: list[str] = []
        err = io.StringIO()
        with (
            mock.patch.dict(spot.STAGES, {stage: {**spec, "records": records_dir}}),
            mock.patch.multiple(
                spot,
                RUNS_DIR=runs,
                DIE=die_path,
                ARTIFACTS=self.home / "layout" / "artifacts.json",
                klt=self._klt,
            ),
            mock.patch.object(spot, "now", return_value=when),
            mock.patch.object(spot, "say", side_effect=said.append),
            mock.patch.object(spot.subprocess, "run", self._run),
            contextlib.redirect_stderr(err),
        ):
            rc = spot.main(argv)
        bundles = sorted(p for p in records_dir.glob("*") if p.is_dir())
        written = [b for b in bundles if (b / "record.json").is_file()]
        return types.SimpleNamespace(
            rc=rc,
            bundles=bundles,
            record=json.loads((written[0] / "record.json").read_text())
            if written
            else None,
            die=json.loads(die_path.read_text()) if die_path.is_file() else None,
            said=said,
            klt_calls=self.klt_calls,
            err=err.getvalue(),
        )

    def _assert_golden(self, got: types.SimpleNamespace, name: str) -> None:
        (bundle,) = got.bundles
        for ext in ("json", "md"):
            with self.subTest(file=ext):
                self.assertEqual(
                    (bundle / f"record.{ext}").read_text(),
                    (FIXTURES / f"{name}.record.{ext}").read_text(),
                )
        self.assertEqual(records.check_intact(bundle), [])
        self.assertFalse((bundle / "INCOMPLETE").exists())

    @staticmethod
    def _headings(markdown: str) -> list[str]:
        return [line for line in markdown.splitlines() if line.startswith("## ")]

    def test_a_passing_build_record_is_the_golden_one(self):
        got = self.record("build")
        self.assertEqual(got.rc, 0)
        self._assert_golden(got, "build-pass")
        self.assertEqual(
            [c[:2] for c in got.klt_calls],
            [("cells", "--format"), ("stats", "--format"), ("artifact", "put")],
        )
        self.assertEqual(Path(got.klt_calls[0][3]).read_bytes(), GDS_BYTES)

    def test_a_passing_precheck_record_is_the_golden_one(self):
        got = self.record("precheck")
        self.assertEqual(got.rc, 0)
        self._assert_golden(got, "precheck-pass")
        self.assertEqual(got.klt_calls, [])

    def test_a_written_record_shares_its_shape_with_the_committed_evidence(self):
        for stage in ("build", "precheck"):
            with self.subTest(stage=stage):
                committed = sorted((LAYOUT / stage / "records").glob("*/record.json"))
                self.assertTrue(committed, f"no {stage} record committed")
                want = json.loads(committed[0].read_text())
                got = self.record(stage, group=stage)
                self.assertEqual(got.rc, 0)
                self.assertEqual(sorted(got.record), sorted(want))
                self.assertEqual(sorted(got.record["job"]), sorted(want["job"]))
                self.assertEqual(
                    self._headings((got.bundles[0] / "record.md").read_text()),
                    self._headings((committed[0].parent / "record.md").read_text()),
                )
                paths = {entry["path"] for entry in got.record["evidence"]}
                self.assertLessEqual(COMMON_EVIDENCE, paths)

    def test_the_exit_code_is_zero_only_for_a_pass(self):
        cases = [
            ("build", "the flow passed", {}, 0, "pass"),
            (
                "build",
                "the flow reported a failure",
                {"job": {**BUILD_JOB, "pass": False}},
                1,
                "fail",
            ),
            ("build", "the job exited non-zero", {"run": {"exit_code": 1}}, 1, "fail"),
            ("build", "no GDS came back", {"gds": False}, 1, "fail"),
            ("build", "an output is missing", {"found": False}, 1, "fail"),
            (
                "build",
                "Spot reclaimed the job",
                {"status": STATUS_RECLAIMED},
                1,
                "error",
            ),
            ("precheck", "the precheck passed", {}, 0, "pass"),
            (
                "precheck",
                "the precheck reported violations",
                {"job": {**PRECHECK_JOB, "pass": False}},
                1,
                "fail",
            ),
            (
                "precheck",
                "Spot reclaimed the job",
                {"status": STATUS_RECLAIMED},
                1,
                "fail",
            ),
            ("precheck", "no precheck.json came back", {"job": None}, 1, "error"),
        ]
        for stage, what, changes, rc, status in cases:
            with self.subTest(stage=stage, case=what):
                self.fresh_home()
                got = self.record(stage, **changes)
                self.assertEqual(got.rc, rc)
                self.assertEqual(got.record["status"], status)
                self.assertEqual(got.record["schema"], spot.STAGES[stage]["schema"])
                self.assertEqual(
                    got.said,
                    [f"wrote {got.bundles[0] / 'record.md'}: status {status}"],
                )
                self.assertEqual(records.check_intact(got.bundles[0]), [])

    def test_a_job_that_died_early_records_what_it_never_reached_as_null(self):
        got = self.record("build", job=None, run={"exit_code": 1})
        self.assertEqual(got.rc, 1)
        for key in ("make", "target", "tools", "metrics"):
            self.assertIn(key, got.record)
            self.assertIsNone(got.record[key])
        for key in ("gds", "checks", "artifact"):
            self.assertNotIn(key, got.record)
        paths = {entry["path"] for entry in got.record["evidence"]}
        self.assertNotIn("build.json", paths)
        self.assertIn("metrics.json", paths)

    def test_a_built_die_that_does_not_match_the_pin_fails_without_an_artifact(self):
        self.cells = {"top_cell_count": 2}
        got = self.record("build")
        self.assertEqual(got.rc, 1)
        self.assertEqual(got.record["status"], "fail")
        self.assertFalse(got.record["checks"]["single_top_cell"])
        self.assertFalse(got.record["checks"]["die_matches_pin"])
        self.assertNotIn("artifact", got.record)
        self.assertEqual(
            [c[:2] for c in got.klt_calls],
            [("cells", "--format"), ("stats", "--format")],
        )

    def test_no_artifact_leaves_the_store_alone(self):
        got = self.record("build", options=("--no-artifact",))
        self.assertEqual(got.rc, 0)
        self.assertNotIn("artifact", got.record)
        self.assertEqual(
            [c[:2] for c in got.klt_calls],
            [("cells", "--format"), ("stats", "--format")],
        )

    def test_a_precheck_of_another_gds_leaves_no_record_behind(self):
        job = {**PRECHECK_JOB, "input": {**PRECHECK_JOB["input"], "sha256": "f" * 64}}
        got = self.record("precheck", job=job)
        self.assertEqual(got.rc, 1)
        self.assertEqual(got.bundles, [])
        self.assertEqual(got.said, [])
        self.assertIn("the job prechecked a different GDS than the one staged", got.err)

    def test_a_record_is_written_once(self):
        first = self.record("build")
        second = self.record("build")
        self.assertEqual((first.rc, second.rc), (0, 1))
        self.assertEqual(second.bundles, first.bundles)
        self.assertIn("File exists", second.err)
        self.assertEqual(second.said, [])
        self.assertEqual(records.check_intact(first.bundles[0]), [])

    def test_the_group_defaults_to_the_shard_s_parent_directory(self):
        got = self.record("build", group="cryo4-build-1", named_group=False)
        self.assertEqual(got.rc, 0)
        self.assertEqual(got.record["job"]["group"], "cryo4-build-1")
        self.assertEqual(got.record["job"]["shard"], "s00")

    def test_a_precheck_record_is_named_after_the_submitted_label(self):
        got = self.record("precheck")
        self.assertEqual(got.bundles[0].name, f"20261126-093000-{SHARD_COMMIT[:7]}-die")
        self.assertEqual(got.record["record_id"], got.bundles[0].name)

    def test_staged_group_refuses_a_missing_or_foreign_submit_record(self):
        runs = self.home / "runs"
        with mock.patch.object(spot, "RUNS_DIR", runs):
            with self.assertRaises(spot.DriverError) as caught:
                spot.staged_group("g", "build")
            self.assertEqual(
                str(caught.exception),
                f"no build submit record for group g under {runs}",
            )
            self._json(runs / "g.submit.json", {"stage": "precheck", "group": "g"})
            with self.assertRaises(spot.DriverError):
                spot.staged_group("g", "build")

    def test_as_die_points_die_json_at_the_new_build(self):
        got = self.record("build", options=("--as-die",))
        self.assertEqual(got.rc, 0)
        die = got.die
        self.assertEqual(die["schema"], "gf180-cryo-char.layout.die/1")
        self.assertEqual(die["gds"], got.record["gds"])
        self.assertEqual(
            die["artifact"],
            {
                "manifest": "layout/artifacts.json",
                "name": got.record["artifact"]["name"],
            },
        )
        self.assertEqual(die["build_record"], got.record["record_id"])
        self.assertIsNone(die["precheck_record"])
        self.assertEqual(
            got.said[-1],
            f"layout/die.json names build {got.record['record_id']}"
            "; it has no precheck record yet",
        )

    def test_as_die_keeps_the_precheck_record_only_for_the_same_gds(self):
        same = {
            "gds": {"name": "chip_top.gds", "sha256": GDS_SHA, "bytes": 1},
            "precheck_record": "20261126-151012-c937349-die",
        }
        kept = self.record("build", die=same, options=("--as-die",))
        self.assertEqual(kept.die["precheck_record"], "20261126-151012-c937349-die")
        self.assertIn("and its precheck record", kept.said[-1])
        moved = self.record(
            "build",
            die={**same, "gds": {**same["gds"], "sha256": "f" * 64}},
            options=("--as-die",),
            when=SHARD_WHEN + dt.timedelta(seconds=1),
        )
        self.assertIsNone(moved.die["precheck_record"])
        self.assertIn("no precheck record yet", moved.said[-1])

    def test_as_die_without_the_artifact_fails_after_the_record_is_written(self):
        die = {"gds": {"sha256": "f" * 64}, "precheck_record": "old"}
        got = self.record("build", die=die, options=("--no-artifact", "--as-die"))
        self.assertEqual(got.rc, 1)
        self.assertEqual(got.record["status"], "pass")
        self.assertEqual(got.die, die)
        self.assertEqual(
            got.said, [f"wrote {got.bundles[0] / 'record.md'}: status pass"]
        )
        self.assertIn(
            "--as-die needs the GDS in the artifact store: drop --no-artifact", got.err
        )

    def test_as_die_ignores_a_record_that_did_not_pass(self):
        got = self.record(
            "build", job={**BUILD_JOB, "pass": False}, options=("--as-die",)
        )
        self.assertEqual(got.rc, 1)
        self.assertIsNone(got.die)
        self.assertEqual(len(got.said), 1)
        self.assertEqual(got.err, "")

    def test_is_die_needs_a_die_pointing_at_the_same_gds(self):
        absent = self.record("precheck", options=("--is-die",))
        self.assertEqual(absent.rc, 1)
        self.assertEqual(absent.record["status"], "pass")
        self.assertIn("there is no layout/die.json to point at this record", absent.err)

        other = {
            "schema": "gf180-cryo-char.layout.die/1",
            "gds": {"name": "chip_top.gds", "sha256": "f" * 64, "bytes": 1},
            "build_record": "20261126-130323-f191663-template",
            "precheck_record": None,
        }
        self.fresh_home()
        got = self.record("precheck", die=other, options=("--is-die",))
        self.assertEqual(got.rc, 1)
        self.assertEqual(got.die, other)
        self.assertIn(
            "the die in layout/die.json is not the GDS this record prechecked", got.err
        )

    def test_is_die_ignores_a_record_that_did_not_pass(self):
        die = {"gds": {"sha256": GDS_SHA}, "precheck_record": "old"}
        got = self.record(
            "precheck",
            die=die,
            job={**PRECHECK_JOB, "pass": False},
            options=("--is-die",),
        )
        self.assertEqual(got.rc, 1)
        self.assertEqual(got.die, die)
        self.assertEqual(len(got.said), 1)

    def test_build_then_precheck_leave_the_die_precheck_clean(self):
        built = self.record("build", options=("--as-die",))
        cleared = self.record("precheck", options=("--is-die",))
        self.assertEqual((built.rc, cleared.rc), (0, 0))
        die = cleared.die
        self.assertEqual(die["build_record"], built.record["record_id"])
        self.assertEqual(die["precheck_record"], cleared.record["record_id"])
        self.assertEqual(die["gds"], built.record["gds"])
        self.assertEqual(die["gds"]["sha256"], cleared.record["input"]["sha256"])
        self.assertEqual(
            cleared.said[-1],
            f"layout/die.json names precheck {cleared.record['record_id']}",
        )


class KltWrapperTests(unittest.TestCase):
    def test_klt_runs_the_command_and_parses_its_json(self):
        done = subprocess.CompletedProcess(
            ["klt", "cells"], 0, stdout='{"top_cell_count": 1}\n', stderr=""
        )
        with mock.patch.object(spot.subprocess, "run", return_value=done) as run:
            self.assertEqual(
                spot.klt("cells", "--format", "json", "a.gds"), {"top_cell_count": 1}
            )
        run.assert_called_once_with(
            ["klt", "cells", "--format", "json", "a.gds"],
            capture_output=True,
            text=True,
        )

    def test_a_failed_klt_call_names_the_command_exit_code_and_stderr(self):
        done = subprocess.CompletedProcess(["klt"], 3, stdout="", stderr="boom\n")
        with (
            mock.patch.object(spot.subprocess, "run", return_value=done),
            self.assertRaises(spot.DriverError) as caught,
        ):
            spot.klt("artifact", "put", "a.gds")
        self.assertEqual(str(caught.exception), "klt artifact put a.gds exited 3: boom")

    def test_artifact_put_goes_through_klt(self):
        entry = {"sha256": GDS_SHA}
        with (
            mock.patch.object(spot, "klt", return_value={"entries": [entry]}) as klt,
            mock.patch.object(
                spot.subprocess,
                "run",
                side_effect=AssertionError("artifact_put() must go through klt()"),
            ),
        ):
            self.assertEqual(
                spot.artifact_put(
                    Path("chip_top.gds"), "build/x/chip_top.gds", "librelane"
                ),
                entry,
            )
        klt.assert_called_once_with(
            "artifact",
            "put",
            "--format",
            "json",
            "--manifest",
            str(spot.ARTIFACTS),
            "--name",
            "build/x/chip_top.gds",
            "--producer-tool",
            "librelane",
            "chip_top.gds",
        )


if __name__ == "__main__":
    unittest.main()
