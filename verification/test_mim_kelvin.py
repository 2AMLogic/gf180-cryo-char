import hashlib
import json
from pathlib import Path
import re
import runpy
import unittest

MIM = Path(__file__).resolve().parents[1] / "layout/mim"
CODES = {"452", "453", "454", "455"}
LAYERS = {"F1": "Metal5", "S1": "Metal5", "F2": "Metal3", "S2": "Metal3"}


class KelvinEvidenceTest(unittest.TestCase):
    def test_macro_aware_power_grid_matches_sources_and_detects_faults(self):
        report = json.loads((MIM / "power-grid.json").read_text())
        for key, name in (("macro_lef", "mim_kelvin.lef"), ("grid_tcl", "power_grid.tcl"),
                          ("verilog", "power_grid.v")):
            self.assertEqual(report["inputs_sha256"][key], hashlib.sha256((MIM / name).read_bytes()).hexdigest())
        verified = json.loads((MIM / "verification.json").read_text())
        units = report["dbu_per_um"]
        for code in CODES:
            left, bottom, right, top = report["macro_bboxes_dbu"][f"mim_{code}_kelvin"]
            self.assertEqual(right - left, round(verified[code]["width_um"] * units))
            self.assertEqual(top - bottom, round(verified[code]["height_um"] * units))
        self.assertEqual(set(report["upper_supply_shapes"]), {"VDD", "VSS"})
        for counts in report["upper_supply_shapes"].values():
            self.assertEqual(set(counts), {"Metal4", "Via4", "Metal5"})
            self.assertTrue(all(value > 0 for value in counts.values()))
        core_nm = json.loads((MIM / "template-grid.json").read_text())["core_nm"]
        self.assertEqual(report["core_dbu"], [round(v * units / 1000) for v in core_nm])
        self.assertEqual(report["macro_outline_contacts"], 0)
        self.assertEqual(report["extracted_supply_nets"], 2)
        self.assertEqual(report["inserted_cross_rail_via_nets"], 1)
        self.assertGreater(report["removed_vss_vias_nets"], 2)

    def test_template_grid_minimum_includes_edge_touching_placements(self):
        measure = runpy.run_path(str(MIM / "template_grid.py"))["minimum_crossings"]
        # Independent integer-grid enumeration covers exact contact at either edge.
        for bands in ([], [(2, 5)], [(0, 1), (3, 7), (10, 12)]):
            for size in range(1, 13):
                brute = min(
                    sum(lo < start + size and hi > start for lo, hi in bands)
                    for start in range(13 - size)
                )
                self.assertEqual(measure(bands, 0, 12, size), brute)

    def test_template_grid_report_matches_lef_and_conductor_intervals(self):
        data = json.loads((MIM / "template-grid.json").read_text())
        self.assertEqual(data["lef_sha256"], hashlib.sha256((MIM / "mim_kelvin.lef").read_bytes()).hexdigest())
        _, low, _, high = data["core_nm"]
        bands = data["full_width_metal5_bands_nm"]
        self.assertEqual(len(bands), 114)
        self.assertTrue(all(low <= lo < hi <= high for lo, hi in bands))
        self.assertTrue(all(pair[0][1] < pair[1][0] for pair in zip(bands, bands[1:])))
        edges = [low, *(y for band in bands for y in band), high]
        self.assertEqual(max(hi - lo for lo, hi in zip(edges[::2], edges[1::2])), 64000)
        self.assertEqual(data["largest_gap_nm"], 64000)
        sizes = json.loads((MIM / "verification.json").read_text())
        self.assertEqual(set(data["macros"]), {f"mim_{code}_kelvin" for code in CODES})
        for code in CODES:
            macro = data["macros"][f"mim_{code}_kelvin"]
            self.assertEqual(macro["size_nm"], [round(sizes[code][key] * 1000) for key in ("width_um", "height_um")])
            self.assertGreater(macro["minimum_crossings_native_orientation"], 0)
            self.assertGreater(macro["minimum_crossings_quarter_turn"], 0)

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
