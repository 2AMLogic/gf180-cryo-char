"""Check that macro evidence follows the exact layout and records both timing cases."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

import klayout.db as db

from flow import check_lvs, reproduce, time_readout

MACRO = reproduce.MACRO


def read_json(path):
    return json.loads(path.read_text())


class RoutedReadout(unittest.TestCase):
    def test_layout_and_drc(self):
        record = reproduce.check_files()
        gds = "sha256:" + record["sha256"]["flow/readout/cryo_char_ctrl.gds"]
        attestation = read_json(
            reproduce.ROOT / "signoff/attest/item2-digital.envelope.json"
        )
        self.assertEqual(attestation["provenance"]["input"]["content_hash"], gds)
        for engine in ("curated", "klayout"):
            report = read_json(MACRO / f"drc-{engine}.json")
            self.assertEqual(report["provenance"]["input"]["content_hash"], gds)
            self.assertEqual(report["dbu_um"], 0.001)
            if engine == "curated":
                self.assertEqual(
                    (report["status"], report["violation_count"]), ("clean", 0)
                )
                self.assertEqual(len(report["coverage"]["checked"]), 72)
            else:
                density = {
                    "DCF.1b",
                    "PL.8",
                    "M1.4",
                    "M2.4",
                    "M3.4",
                    "M4.4",
                    "M5.4",
                    "MT.3",
                }
                self.assertEqual(report["status"], "violations")
                self.assertEqual(report["rule_counts"], dict.fromkeys(density, 1))
                self.assertEqual(report["violation_count"], len(density))

    def test_routed_lvs(self):
        report = read_json(MACRO / "lvs.report.json")
        check_lvs.verify(report)
        self.assertEqual(
            report["provenance"]["input"]["content_hash"],
            "sha256:" + reproduce.sha(MACRO / "cryo_char_ctrl.gds"),
        )

    def test_grid_conversion_rejects_lost_metal(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "original.gds"
            result = Path(tmp) / "converted.gds"
            layout = db.Layout()
            layout.dbu = 0.0005
            top = layout.create_cell(reproduce.TOP)
            shapes = top.shapes(layout.layer(34, 0))
            shapes.insert(db.Box(0, 0, 40, 40))
            layout.write(str(source))
            reproduce.shuttle_stream(source, result)
            shapes.insert(db.Box(41, 0, 51, 21))
            layout.write(str(source))
            with self.assertRaisesRegex(ValueError, "Drawn masks differ"):
                reproduce.shuttle_stream(source, result)

    def test_measured_and_stressed_timing(self):
        spef = MACRO / "cryo_char_ctrl.spef"
        extraction = read_json(MACRO / "extraction.json")
        self.assertEqual(extraction["spef"]["sha256"], reproduce.sha(spef))
        self.assertEqual(
            extraction["def_sha256"], reproduce.sha(MACRO / "cryo_char_ctrl.def")
        )
        self.assertEqual(
            extraction["provenance"]["input"]["content_hash"],
            "sha256:" + reproduce.sha(MACRO / "cryo_char_ctrl.gds"),
        )
        with (MACRO / "ring-step-control.csv").open() as f:
            minimum = {
                r["family"]: float(r["min_period_ns"])
                for r in csv.DictReader(f)
                if float(r["step_ns"]) == 0.000625
            }
        for name in ("timing", "timing-stress"):
            request = read_json(MACRO / f"{name}.json")
            report = read_json(MACRO / f"{name}.report.json")
            self.assertEqual(
                report["timing_input_sha256"],
                time_readout.input_hashes(MACRO / f"{name}.json"),
            )
            self.assertEqual(
                report["provenance"]["input"]["content_hash"],
                "sha256:" + reproduce.sha(MACRO / request["def"]),
            )
            self.assertEqual(
                report["spef_path"]["path"], spef.relative_to(reproduce.ROOT).as_posix()
            )
            clocks = request["constraints"]["clocks"]
            self.assertEqual(report["clock_targets"]["clocks"], clocks)
            self.assertEqual(
                report["clock_targets"]["clock_groups"], [[c["port"]] for c in clocks]
            )
            periods = {c["port"]: c["period_ns"] for c in clocks}
            self.assertEqual(set(periods), {"clk"} | {f"ro_clk[{i}]" for i in range(8)})
            for index, family in enumerate(("7t", "9t", "9t", "12t") * 2):
                bound = minimum[family]
                period = periods[f"ro_clk[{index}]"]
                self.assertLessEqual(period, bound)
                if name == "timing":
                    self.assertLessEqual(period, 0.98 * bound)
            corners = {c["corner"]: c for c in report["corners"]}
            self.assertEqual(set(corners), set(request["pdk"]["corners"]))
            self.assertEqual(len(corners), 5)
            for corner in corners.values():
                annotation = corner["spef_annotation"]
                self.assertTrue(annotation["annotation_complete"])
                self.assertEqual(
                    (annotation["nets_annotated"], annotation["nets_total"]), (596, 596)
                )
                self.assertEqual(annotation["reader_warning_count"], 0)
                self.assertEqual(
                    corner["constraint_completeness"]["unconstrained_endpoints"][
                        "count"
                    ],
                    65,
                )
                self.assertGreater(corner["worst_hold_slack_ns"], 0)
                self.assertEqual(corner["hold_violation_count"], 0)
                if name == "timing-stress" and corner["corner"] == "ss_125C_3v00":
                    self.assertLess(corner["worst_slack_ns"], 0)
                    self.assertEqual(corner["setup_violation_count"], 4)
                else:
                    self.assertGreater(corner["worst_slack_ns"], 0)
                    self.assertEqual(corner["setup_violation_count"], 0)
