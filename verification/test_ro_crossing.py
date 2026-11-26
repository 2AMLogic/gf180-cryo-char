import csv
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CELL = ROOT / "design/ro-crossing"


class RingCrossing(unittest.TestCase):
    def test_measurements_use_these_source_views(self):
        manifest = json.loads((CELL / "measurements.manifest.json").read_text())
        for name, expected in manifest["sha256"].items():
            with self.subTest(name=name):
                self.assertEqual(
                    hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected
                )
        gds_hash = "sha256:" + manifest["sha256"]["design/ro-crossing/efuse_ls.gds"]
        for name in ("extract.report", "lvs.report", "drc-curated", "drc-native"):
            report = json.loads((CELL / f"{name}.json").read_text())
            self.assertEqual(report["provenance"]["input"]["content_hash"], gds_hash)
        lvs = json.loads((CELL / "lvs.report.json").read_text())
        self.assertEqual((lvs["status"], lvs["error_count"]), ("match", 0))
        for kind, count in (("devices", 6), ("pins", 5), ("nets", 7)):
            self.assertEqual(set(lvs["counts"][kind].values()), {count})

    def test_low_ring_voltage_captures_with_the_translator(self):
        with (CELL / "measurements.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 46)
        for r in rows:
            self.assertGreater(int(r["capture_windows"]), 0)
            self.assertEqual(
                int(r["windows_with_one_toggle"]), int(r["capture_windows"])
            )
        split = [
            r
            for r in rows
            if r["pdk_source"] == "open_pdks"
            and r["crossing"] == "extracted"
            and r["process"] == "ff"
            and float(r["vro_v"]) == 1.4
            and float(r["logic_v"]) == 3.6
            and float(r["step_ns"]) == 0.04
        ]
        self.assertEqual(sorted(int(r["port"]) for r in split), list(range(8)))
        self.assertEqual(sum(int(r["capture_windows"]) for r in split), 158)
        self.assertTrue(all(float(r["shifter_ring_supply_ua"]) > 0.100 for r in split))
        with (ROOT / "flow/readout/routed-ring-capture.csv").open() as stream:
            direct = [
                r
                for r in csv.DictReader(stream)
                if r["process"] == "ff"
                and float(r["vro_v"]) == 1.4
                and float(r["logic_v"]) == 3.6
            ]
        self.assertEqual(sorted(int(r["port"]) for r in direct), list(range(8)))
        self.assertEqual(sum(int(r["windows"]) for r in direct), 158)
        self.assertEqual(sum(int(r["captures"]) for r in direct), 0)

    def test_separate_feed_still_loads_the_oscillator(self):
        key = ("family", "process", "temperature_c", "vro_v", "step_ns", "duration_ns")
        with (CELL / "unloaded.csv").open() as stream:
            controls = {
                tuple(r[k] for k in key): float(r["average_vro_current_ua"])
                for r in csv.DictReader(stream)
            }
        self.assertEqual(len(controls), 12)
        comparisons = 0
        with (CELL / "measurements.csv").open() as stream:
            for r in csv.DictReader(stream):
                if r["pdk_source"] != "open_pdks" or r["crossing"] != "extracted":
                    continue
                unloaded = controls.get(tuple(r[k] for k in key))
                if unloaded is None:
                    continue
                net = float(r["average_vro_current_ua"]) - float(
                    r["shifter_ring_supply_ua"]
                )
                self.assertGreater(net - unloaded, 0.100)
                comparisons += 1
        self.assertEqual(comparisons, 32)
