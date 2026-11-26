import hashlib
import json
from pathlib import Path
import re
import unittest

MIM = Path(__file__).resolve().parents[1] / "layout/mim"
CODES = {"452", "453", "454", "455"}
LAYERS = {"F1": "Metal5", "S1": "Metal5", "F2": "Metal3", "S2": "Metal3"}


class KelvinEvidenceTest(unittest.TestCase):
    def test_access_and_drc_share_the_verified_layout(self):
        def record(name):
            return json.loads((MIM / name).read_text())

        parent = record("verification.json")
        access = record("kelvin-access.json")
        drc = record("kelvin-drc.json")
        for report in (parent, access, drc):
            self.assertEqual(set(report), CODES)
        for code in CODES:
            with self.subTest(code=code):
                source = hashlib.sha256(
                    (MIM / f"mim_{code}.gds").read_bytes()
                ).hexdigest()
                self.assertEqual(source, parent[code]["sha256"])
                self.assertEqual(source, access[code]["source_sha256"])
                self.assertRegex(access[code]["gds_sha256"], r"^[a-f0-9]{64}$")
                self.assertEqual(access[code]["gds_sha256"], drc[code]["gds_sha256"])
                self.assertEqual(
                    access[code]["capacitors_probed"], parent[code]["units"]
                )
                self.assertEqual(access[code]["isolated_by_cut"], sorted(LAYERS))
                self.assertIs(access[code]["interplate_short_detected"], True)
                for name, count in (("native", 763), ("curated", 25)):
                    self.assertEqual(drc[code][name]["rule_categories"], count)
                    self.assertEqual(drc[code][name]["violations"], 0)

    def test_lef_contains_each_complete_macro_and_terminal(self):
        text = (MIM / "mim_kelvin.lef").read_text()
        self.assertTrue(text.rstrip().endswith("END LIBRARY"))
        macros = re.findall(
            r"(?ms)^MACRO mim_(\d+)_kelvin\n(.*?)^END mim_\1_kelvin$", text
        )
        self.assertCountEqual([code for code, _ in macros], CODES)
        parent = json.loads((MIM / "verification.json").read_text())
        for code, macro in macros:
            with self.subTest(code=code):
                size = re.findall(r"(?m)^  SIZE ([.\d]+) BY ([.\d]+) ;$", macro)
                self.assertEqual(len(size), 1)
                width, height = map(float, size[0])
                self.assertEqual(
                    (width, height),
                    (parent[code]["width_um"], parent[code]["height_um"]),
                )
                pins = re.findall(r"(?ms)^  PIN (\w+)\n(.*?)^  END \1$", macro)
                self.assertCountEqual([name for name, _ in pins], LAYERS)
                for name, pin in pins:
                    self.assertEqual(pin.count("PORT"), 1)
                    self.assertEqual(re.findall(r"LAYER (\w+) ;", pin), [LAYERS[name]])
                    rectangles = re.findall(r"RECT ([.\d ]+) ;", pin)
                    self.assertEqual(len(rectangles), 1)
                    xl, yb, xr, yt = map(float, rectangles[0].split())
                    self.assertTrue(0 <= xl < xr <= width and 0 <= yb < yt <= height)
                    self.assertEqual(
                        xr if name.endswith("1") else xl,
                        width if name.endswith("1") else 0,
                    )
                    self.assertEqual(
                        yb if name.startswith("F") else yt,
                        2 if name.startswith("F") else height - 2,
                    )
