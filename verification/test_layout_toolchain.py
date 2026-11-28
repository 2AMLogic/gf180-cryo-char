"""layout/ pin, evidence-record and die-consistency checks (issue #4)."""

import datetime as dt
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from layout import records, toolchain_pin

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

    def test_report_returns_the_pins_it_checked(self):
        out = io.StringIO()
        rc, pins = toolchain_pin.report(help_text=KLT_HELP, stdout=out)
        self.assertEqual(rc, 0)
        self.assertEqual(pins, toolchain_pin.load(LAYOUT))
        self.assertIn("toolchain.json: OK", out.getvalue())
        precheck = pins["wafer_space"]["precheck"]["commit"][:7]
        self.assertIn(f"  precheck {precheck}", out.getvalue())

    def test_report_keeps_the_pins_when_a_pinned_command_is_missing(self):
        trimmed = KLT_HELP.replace(
            "    artifact            ", "    zrtifact            "
        )
        err = io.StringIO()
        rc, pins = toolchain_pin.report(help_text=trimmed, stderr=err)
        self.assertEqual(rc, 1)
        self.assertEqual(pins, toolchain_pin.load(LAYOUT))
        self.assertIn("'artifact'", err.getvalue())
        self.assertIn("uv tool install " + pins["klt_install"], err.getvalue())

    def test_report_returns_no_pins_when_the_check_fails(self):
        err = io.StringIO()
        rc, pins = toolchain_pin.report(klt="/nonexistent/klt", stderr=err)
        self.assertEqual(rc, 1)
        self.assertIsNone(pins)
        self.assertIn("error: cannot run `/nonexistent/klt --help`", err.getvalue())

    def test_main_rejects_any_argv_but_check(self):
        out, err = io.StringIO(), io.StringIO()
        rc = toolchain_pin.main(["--check", "extra"], stdout=out, stderr=err)
        self.assertEqual(rc, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("usage: ", err.getvalue())
        self.assertIn("[--check]", err.getvalue())


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


if __name__ == "__main__":
    unittest.main()
