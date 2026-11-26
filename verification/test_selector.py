import tempfile
import unittest
from pathlib import Path

from cocotb_tools.runner import get_results, get_runner

from rtl.regenerate import simulate


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

    def test_ring_readout(self):
        with tempfile.TemporaryDirectory() as build_dir:
            sources = [ROOT / "rtl/selector.v", ROOT / "rtl/cryo_char_ctrl.v"]
            simulate(Path(build_dir), sources)
            simulate(Path(build_dir), sources, flags=["-DCHECK_RING_CUTS"])

    def test_full_map(self):
        self.run_selector([])

    def test_all_paths_cut(self):
        self.run_selector(range(1024))

    def test_each_cut_address_bit(self):
        # Each address has a unique ten-bit signature. Applying its bitplanes
        # as cut masks exposes a swapped cut (including open vs short).
        for bit in range(10):
            with self.subTest(bit=bit):
                self.run_selector([addr for addr in range(1024) if addr & (1 << bit)])
