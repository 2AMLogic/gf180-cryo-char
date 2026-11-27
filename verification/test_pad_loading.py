import csv
from itertools import product
from pathlib import Path
import unittest


DATA = Path(__file__).resolve().parents[1] / "sim/pad-loading/measurements.csv"


class PadLoadingTest(unittest.TestCase):
    def test_signed_pad_grid_and_numerical_controls(self):
        with DATA.open() as stream:
            rows = list(csv.DictReader(stream))
        main = [r for r in rows if float(r["gmin_s"]) == 1e-18]
        expected = [
            (corner, temp, rail, round(fraction * rail, 6))
            for corner, temp, rail, fraction in product(
                ("typical", "ss", "ff"),
                (-40, 25, 125),
                (3, 3.3, 3.6),
                (0, 0.25, 0.5, 0.75, 1),
            )
        ]
        keys = [
            (r["diode_corner"], int(r["temp_c"]), float(r["dvdd_v"]), float(r["pad_v"]))
            for r in main
        ]
        self.assertCountEqual(keys, expected)
        controls = [r for r in rows if float(r["gmin_s"]) != 1e-18]
        self.assertCountEqual(
            [
                (
                    r["diode_corner"],
                    float(r["dvdd_v"]),
                    int(r["temp_c"]),
                    float(r["pad_v"]),
                    float(r["gmin_s"]),
                )
                for r in controls
            ],
            product(["typical"], [3.3], [-40, 25, 125], [0, 1.65, 3.3], [1e-12, 1e-21]),
        )
        for r in rows:
            self.assertAlmostEqual(
                float(r["d2_a"]) - float(r["d3_a"]),
                float(r["clamp_net_a"]),
                delta=1e-24,
            )
        worst = max(main, key=lambda r: abs(float(r["clamp_net_a"])))
        self.assertEqual(
            (worst["diode_corner"], worst["temp_c"], worst["pad_v"]),
            ("ff", "125", "3.6"),
        )
        self.assertAlmostEqual(float(worst["clamp_net_a"]) * 1e12, -107.45, delta=0.01)
