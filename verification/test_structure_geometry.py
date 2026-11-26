import re
import unittest
from pathlib import Path


# W and L in micrometres from open_pdks f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7,
# gf180mcuD/libs.tech/klayout/tech/pymacros/cells/{fet,res}.py.
MINIMUM_WL = {
    "nfet_03v3": (0.22, 0.28),
    "pfet_03v3": (0.22, 0.28),
    "nfet_06v0": (0.30, 0.70),
    "pfet_06v0": (0.30, 0.55),
    "nfet_06v0_nvt": (0.80, 1.80),
    "ppolyf_u": (0.80, 0.80),
    "ppolyf_u_1k": (1.00, 1.00),
}
MAP = Path(__file__).resolve().parents[1] / "spec" / "structure-map.md"


class DrawnGeometryTest(unittest.TestCase):
    def test_fet_and_resistor_targets_fit_the_pcell(self):
        devices = set()
        for line in MAP.read_text().splitlines():
            if not re.match(r"^\| \d+ \|", line):
                continue
            code, cell, _, _, _, _, target = (s.strip() for s in line.strip("|").split("|"))
            if cell.split("!")[0] not in {"FETModules", "ISOFETs", "MOSCAPs", "MOSCAPOVLs", "PrRES"}:
                continue
            if target.startswith(("Dropped", "Cut")):
                continue
            with self.subTest(code=code, cell=cell):
                device, geometry = target.split(", ", 1)
                self.assertIn(device, MINIMUM_WL)
                dims = re.match(r"(?:five parallel )?([\d.]+) × ([\d.]+)\b", geometry)
                self.assertIsNotNone(dims, f"missing drawn W × L in {target}")
                width, length = map(float, dims.groups())
                min_width, min_length = MINIMUM_WL[device]
                self.assertGreaterEqual(width, min_width)
                self.assertGreaterEqual(length, min_length)
                devices.add(device)
        self.assertEqual(devices, set(MINIMUM_WL))
