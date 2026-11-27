import csv
import hashlib
import itertools
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIM = ROOT / "layout/mim"
SPECIMENS = {"452": (5, 40), "453": (5, 40), "454": (3920, 5), "455": (1620, 10)}
NIST_BY_CODE = {
    "452": "AreaMIMC1",
    "453": "AreaMIMC2",
    "454": "PeriMIMC1",
    "455": "PeriMIMC2",
}


class MimSpecimensTest(unittest.TestCase):
    def test_streams_and_physical_evidence(self):
        evidence = json.loads((MIM / "verification.json").read_text())
        self.assertEqual(set(evidence), set(SPECIMENS))
        self.assertEqual(len({r["sha256"] for r in evidence.values()}), 4)
        for code, (count, side) in SPECIMENS.items():
            with self.subTest(code=code):
                row = evidence[code]
                gds = (MIM / f"mim_{code}.gds").read_bytes()
                self.assertGreater(len(gds), 0)
                self.assertEqual(hashlib.sha256(gds).hexdigest(), row["sha256"])
                self.assertEqual((row["units"], row["unit_side_um"]), (count, side))
                self.assertEqual(row["total_plate_area_um2"], count * side**2)
                self.assertEqual(row["total_plate_perimeter_um"], count * 4 * side)
                self.assertEqual(set(row["compared"]), {"A", "P"})
                for item, total in (("pins", 2), ("nets", 2), ("devices", count)):
                    self.assertEqual(row["lvs"][item], dict(layout=total, matched=total, reference=total))
                self.assertEqual(row["open_lvs"]["nets"]["layout"], 3)
                self.assertLess(row["open_lvs"]["devices"]["matched"], count)
                self.assertEqual((row["drc_categories"], row["drc_violations"]), (763, 0))
                self.assertEqual((row["curated_categories"], row["curated_violations"]), (25, 0))

    def test_extracted_ac_grid(self):
        with (MIM / "measurements.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        cases = list(itertools.product(
            SPECIMENS, ("mimcap_ff", "mimcap_typical", "mimcap_ss"),
            ("-40", "25", "125"), ("0", "1.65", "3.3"),
        ))
        keys = [(r["code"], r["mim_corner"], r["temp_c"], r["bias_v"]) for r in rows]
        self.assertCountEqual(keys, cases)
        capacitance = {key: float(row["capacitance_pf"]) for key, row in zip(keys, rows)}
        for (code, corner, temp, bias), value in capacitance.items():
            with self.subTest(code=code, corner=corner, temp=temp, bias=bias):
                count, side = SPECIMENS[code]
                area_pf = 0.002 * count * side**2
                self.assertTrue(0.85 * area_pf < value < 1.25 * area_pf)
                if code == "452":
                    self.assertAlmostEqual(value, capacitance["453", corner, temp, bias])

    def test_klt_sim_batch_record_and_toolchain(self):
        toolchain = json.loads((ROOT / "layout/toolchain.json").read_text())
        self.assertIn("sim", toolchain["klt_required_commands"])

        records = sorted((MIM / "records").glob("*/manifest.json"))
        self.assertGreaterEqual(len(records), 1)
        rec_dir = records[-1].parent
        manifest = json.loads((rec_dir / "manifest.json").read_text())
        envelope_bytes = (rec_dir / manifest["envelope_file"]).read_bytes()
        self.assertEqual(hashlib.sha256(envelope_bytes).hexdigest(), manifest["envelope_sha256"])
        envelope = json.loads(envelope_bytes)

        self.assertEqual(envelope["status"], "pass")
        self.assertEqual((envelope["corner_count"], envelope["passed"]), (27, 27))
        self.assertEqual((envelope["failed"], envelope["errored"], envelope["inconclusive"]), (0, 0, 0))
        self.assertEqual(envelope["diagnostic_counts"]["corners_with_diagnostics"], 0)
        self.assertEqual(envelope["environment"]["netlist_identity"], manifest["netlist_identity"])
        self.assertEqual(envelope["environment"]["backend"]["resolved"], "batch")
        remote = envelope["environment"]["remote"]
        self.assertEqual(remote["state"], "done")
        self.assertTrue(remote["job_id"])
        self.assertEqual(remote["job_id"], manifest["remote_job_id"])

        verified = json.loads((MIM / "verification.json").read_text())
        closure_shas = {entry["sha256"] for entry in envelope["environment"]["netlist_closure"]}
        self.assertEqual(set(manifest["structures"]), set(NIST_BY_CODE.values()))
        rollup_by_name = {m["name"]: m for m in envelope["measurements"]}
        self.assertEqual(set(rollup_by_name), set(NIST_BY_CODE.values()))

        with (MIM / "measurements.csv").open() as stream:
            csv_caps = {
                (r["code"], r["mim_corner"], r["temp_c"], r["bias_v"]): float(r["capacitance_pf"])
                for r in csv.DictReader(stream)
            }

        for code, nist_id in NIST_BY_CODE.items():
            with self.subTest(nist_id=nist_id):
                entry = manifest["structures"][nist_id]
                self.assertEqual(entry["select_code"], int(code))
                self.assertEqual(entry["gds_sha256"], verified[code]["sha256"])
                self.assertIn(entry["extracted_spice_sha256"], closure_shas)
                self.assertEqual(rollup_by_name[nist_id]["spec_row"], code)
                self.assertEqual(rollup_by_name[nist_id]["status"], "pass")
                self.assertEqual(len(entry["points"]), 27)
                for pt in entry["points"]:
                    key = (code, pt["mim_corner"], str(pt["temp_c"]), str(pt["bias_v"]))
                    self.assertAlmostEqual(pt["capacitance_pf"], csv_caps[key], places=6)

        for corner in envelope["corners"]:
            proc = corner["process"]
            temp = str(int(corner["temperature_c"]) if float(corner["temperature_c"]).is_integer() else corner["temperature_c"])
            bias = corner["supply_v"]["vbias"]
            bias_s = str(int(bias) if float(bias).is_integer() else bias)
            by_name = {m["name"]: m["value"] for m in corner["measurements"]}
            for code, nist_id in NIST_BY_CODE.items():
                self.assertAlmostEqual(by_name[nist_id], csv_caps[code, proc, temp, bias_s], places=6)
