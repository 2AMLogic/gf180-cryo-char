import csv
import hashlib
import itertools
import json
from pathlib import Path
import unittest


MIM = Path(__file__).resolve().parents[1] / "layout/mim"
SPECIMENS = {"452": (5, 40), "453": (5, 40), "454": (3920, 5), "455": (1620, 10)}


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
