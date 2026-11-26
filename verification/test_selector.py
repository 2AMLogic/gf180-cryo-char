import tempfile
import unittest
from pathlib import Path

from cocotb_tools.runner import get_results, get_runner


ROOT = Path(__file__).resolve().parents[1]


class SelectorTest(unittest.TestCase):
    def run_selector(self, cuts):
        with tempfile.TemporaryDirectory() as build_dir:
            runner = get_runner("icarus")
            cut_mask = sum(1 << code for code in cuts)
            runner.build(
                sources=[ROOT / "rtl/selector.v"], hdl_toplevel="cryo_selector",
                build_dir=build_dir, parameters={"CUT_PATHS": f"1024'h{cut_mask:x}"},
            )
            result = runner.test(
                test_module="selector_cocotb", hdl_toplevel="cryo_selector",
                extra_env={"SELECTOR_CUTS": ",".join(map(str, cuts))}, seed=1,
            )
            self.assertEqual(get_results(result), (1, 0))

    def test_full_map(self):
        self.run_selector([])

    def test_independent_freeze_cuts(self):
        self.run_selector([2, 456, 994])  # A primary, one resistor placement, one RO replica.
