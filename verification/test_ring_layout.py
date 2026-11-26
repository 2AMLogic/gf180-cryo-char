import csv
import hashlib
import itertools
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RINGS = ROOT / "design/rings"


class PhysicalRings(unittest.TestCase):
    def test_evidence_names_the_shipped_views(self):
        receipts = json.loads((RINGS / "verification.json").read_text())
        for family, evidence in receipts.items():
            for ext, key in (
                ("gds", "gds_sha256"),
                ("spice", "reference_sha256"),
                ("pex.spice", "pex_sha256"),
            ):
                self.assertEqual(
                    hashlib.sha256(
                        (RINGS / f"ro_{family}.{ext}").read_bytes()
                    ).hexdigest(),
                    evidence[key],
                )
            self.assertEqual(set(evidence["port_centres"]), {"en", "out", "vro", "vss"})
            self.assertEqual(evidence["native"]["checked_categories"], 763)
            self.assertEqual(
                (evidence["native"]["status"], evidence["native"]["violations"]),
                ("clean", 0),
            )
            self.assertEqual(evidence["lvs"]["devices"]["matched"], 292)
            self.assertEqual(evidence["lvs"]["nets"]["matched"], 149)
            self.assertEqual(evidence["feedback_open_lvs"]["nets"]["layout"], 150)
        self.assertEqual(
            receipts["12t"]["curated"]["rules"],
            {"nplus.enclosing.comp.1": 294, "pplus.space.ncomp.1": 146},
        )
        inputs = json.loads((RINGS / "measurements.manifest.json").read_text())
        for path, digest in inputs["sha256"].items():
            self.assertEqual(
                hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path
            )

    def test_capture_grid_and_metrology_controls(self):
        with (RINGS / "measurements.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 68)
        high = {
            (r["family"], r["process"], int(r["temperature_c"]))
            for r in rows
            if r["vro_v"] == "3.6"
        }
        self.assertEqual(
            high,
            set(
                itertools.product(
                    ("7t", "9t", "12t"),
                    ("typical", "ff", "ss", "fs", "sf"),
                    (-40, 25, 125),
                )
            ),
        )
        corners = {
            int(r["port"])
            for r in rows
            if r["receiver"] == "extracted"
            and r["process"] == "ff"
            and r["vro_v"] == "1.4"
        }
        self.assertEqual(corners, set(range(8)))
        for r in rows:
            if r["receiver"] in ("direct", "extracted"):
                self.assertGreater(int(r["capture_windows"]), 0)
                expected = 0 if r["receiver"] == "direct" else int(r["capture_windows"])
                self.assertEqual(int(r["windows_with_one_toggle"]), expected)
            elif r["receiver"] == "disabled":
                self.assertEqual(int(r["rising_edges"]), 0)
        for port in ("0", "2", "3"):
            split = {
                r["receiver"]: r
                for r in rows
                if r["port"] == port and r["process"] == "ff" and r["vro_v"] == "1.4"
            }
            measured = split["extracted"]
            residual = (
                float(measured["average_vro_current_ua"])
                - float(measured["shifter_ring_supply_ua"])
                - float(split["unloaded"]["average_vro_current_ua"])
            )
            self.assertGreater(residual, 0.100)
