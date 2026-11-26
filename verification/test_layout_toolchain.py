"""layout/ pin, evidence-record and die-consistency checks (issue #4)."""

import datetime as dt
import io
import json
import tempfile
import unittest
from pathlib import Path

from layout import records, toolchain_pin

REPO = Path(__file__).resolve().parents[1]
LAYOUT = REPO / "layout"

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
        pointer = LAYOUT / "die.json"
        if not pointer.is_file():
            self.skipTest("no die recorded on this branch yet")
        die = json.loads(pointer.read_text())
        gds_sha = die["gds"]["sha256"]
        precheck = (
            LAYOUT / "precheck" / "records" / die["precheck_record"] / "record.json"
        )
        record = json.loads(precheck.read_text())
        self.assertEqual(record["status"], "pass")
        self.assertEqual(record["input"]["sha256"], gds_sha)
        build = json.loads(
            (
                LAYOUT / "build" / "records" / die["build_record"] / "record.json"
            ).read_text()
        )
        self.assertEqual(build["status"], "pass")
        self.assertEqual(build["gds"]["sha256"], gds_sha)
        stored = [
            e["sha256"]
            for e in json.loads((LAYOUT / "artifacts.json").read_text())["entries"]
        ]
        self.assertIn(
            gds_sha,
            stored,
            "the die's GDS is not retrievable from the artifact manifest",
        )


if __name__ == "__main__":
    unittest.main()
