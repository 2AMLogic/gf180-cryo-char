import csv
from math import hypot
from pathlib import Path
import unittest


DATA = Path(__file__).resolve().parents[1] / "sim/switch-loading/mismatch.csv"


class SwitchMismatchTest(unittest.TestCase):
    def test_recorded_polarities_and_p95_upper_bounds(self):
        groups = {}
        with DATA.open() as stream:
            for row in csv.DictReader(stream):
                bias = (
                    row["process"],
                    int(row["temp_c"]),
                    float(row["sense_v"]),
                    float(row["far_v"]),
                )
                groups.setdefault(bias, []).append(row)
        expected = {
            ("typical", 25, 0, 0): (1, 0.254129, 6.499928),
            ("ff", 125, 0, 3.3): (1, 191.863711, 54.763183),
            ("ff", 125, 3.3, 0): (-1, 195.298087, 7.755439),
        }
        self.assertEqual(set(groups), set(expected))
        for bias, (sign, dc_bound, ac_bound) in expected.items():
            with self.subTest(bias=bias):
                rows = groups[bias]
                self.assertCountEqual([int(r["seed"]) for r in rows], range(1001, 1129))
                signed = [float(r["dc_a"]) for r in rows]
                self.assertTrue(all(sign * value > 0 for value in signed))
                dc = sorted(abs(value) * 1e12 for value in signed)
                ac = sorted(
                    hypot(float(r["real_a"]), float(r["imag_a"])) * 1e12 for r in rows
                )
                self.assertAlmostEqual(dc[125], dc_bound, delta=1e-6)
                self.assertAlmostEqual(ac[125], ac_bound, delta=1e-6)
