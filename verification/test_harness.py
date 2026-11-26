"""Exercise the characterization harness with disposable, synthetic data."""

import json
import tempfile
import unittest
from pathlib import Path

from sim.harness import report, testbench
from sim.harness.corners import CORNERS, PvtPoint
from sim.harness.pdk import Pdk
from sim.harness.runner import PointResult


class HarnessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bench_dir = self.root / "fixture" / "testbench"
        self.bench_dir.mkdir(parents=True)
        (self.bench_dir / "fixture.spice").write_text("Rfixture out 0 1k\n")
        self.manifest = self.bench_dir / "tb.json"
        self.manifest.write_text(json.dumps({
            "netlist": "fixture.spice",
            "measure": {"voltage": "v(out)"},
            "checks": {"voltage": {"min": 0.5}},
            "corners": ["tt"],
            "temperatures_c": [25],
            "nominal_supply_v": 3.3,
            "supply_tolerance": 0,
        }))

    def test_duplicate_limits_are_rejected(self):
        self.manifest.write_text('{"checks":{"voltage":{"min":0.5,"min":0}}}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            testbench.load(self.bench_dir)

    def test_nonfinite_measurement_limit_is_rejected(self):
        self.manifest.write_text(self.manifest.read_text().replace("0.5", "NaN"))
        with self.assertRaises(ValueError):
            testbench.load(self.bench_dir)

    def test_corner_record_and_missing_result(self):
        bench = testbench.load(self.bench_dir)
        point = PvtPoint(CORNERS["tt"], 25, 3.3)
        pdk = Pdk("fixture", self.root, "fixture", "test fixture", "unused.lib")
        cases = [
            ([PointResult(point, "ok", {"voltage": 0.75})], "pass"),
            ([PointResult(point, "ok", {"voltage": 0.25})], "fail"),
            ([], "error"),
        ]
        for results, expected in cases:
            with self.subTest(expected=expected):
                record = report.build_record(
                    bench, pdk, [point], results, ngspice="fixture",
                    repo_root=self.root, record_id="fixture-" + expected,
                    started_utc="2000-01-01T00:00:00Z", wall_seconds=0,
                    git={"commit": "fixture", "dirty": False},
                )
                self.assertEqual(record["status"], expected)
                self.assertEqual(record["reconciliation"]["complete"], bool(results))
                saved = report.write_record(record, bench.experiment_dir)
                self.assertIn(f"**Status**: {expected}", saved.read_text())
                with self.assertRaises(report.RecordExists):
                    report.write_record(record, bench.experiment_dir)


class CommittedBenchTests(unittest.TestCase):
    def test_shipped_manifests(self):
        sim_dir = Path(__file__).resolve().parents[1] / "sim"
        for experiment in testbench.discover(sim_dir):
            with self.subTest(experiment=experiment.name):
                testbench.load(experiment)
