import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CELL = ROOT / "design/ro-isolation"
SPEC = importlib.util.spec_from_file_location("ro_isolation", CELL / "measure.py")
MEASURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MEASURE)


class ReadoutIsolation(unittest.TestCase):
    def test_physical_controls_and_provenance(self):
        receipts = json.loads((CELL / "verification.json").read_text())
        self.assertEqual(set(receipts), {"7t", "9t", "12t"})
        for family, receipt in receipts.items():
            for suffix, field in (
                ("gds", "gds"),
                ("spice", "schematic"),
                ("pex.spice", "pex"),
            ):
                digest = hashlib.sha256(
                    (CELL / f"ro_{family}_read.{suffix}").read_bytes()
                ).hexdigest()
                self.assertEqual(digest, receipt[field + "_sha256"])
            self.assertEqual(receipt["lvs"]["pins"]["matched"], 6)
            self.assertEqual(receipt["lvs"]["devices"]["matched"], 294)
            self.assertEqual(
                receipt["feedback_to_receiver_open"]["nets"]["layout"], 153
            )
            self.assertEqual(receipt["native"]["violations"], 0)
            self.assertEqual(receipt["native"]["checked_categories"], 763)
        manifest = json.loads((CELL / "measurements.manifest.json").read_text())
        for path, digest in manifest["sha256"].items():
            self.assertEqual(
                hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path
            )

    def test_current_limits_and_receiver_controls(self):
        with (CELL / "measurements.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        points = [
            tuple(
                r[k] if k in ("mode", "process") else float(r[k])
                for k in MEASURE.INPUTS
            )
            for r in rows
        ]
        self.assertEqual(points, list(MEASURE.points()))
        for row in rows:
            windows = int(row["capture_windows"])
            self.assertGreater(windows, 0)
            if row["mode"] in ("read", "original"):
                self.assertEqual(int(row["windows_with_one_toggle"]), windows)
            else:
                self.assertLess(
                    float(row["translated_high_v"]), float(row["logic"]) / 2
                )
                self.assertLess(float(row["rx_max"]), 0.005)
                self.assertEqual(int(row["windows_with_one_toggle"]), 0)
        errors = MEASURE.current_errors(rows)
        self.assertEqual(len(errors), 24)
        for (_, _, _, vro, _, _, _), added in errors.items():
            self.assertEqual(abs(added) <= 0.100, vro <= 1.8)
