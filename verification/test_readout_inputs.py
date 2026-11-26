import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sim.readout import cold_start


class ReadoutInputsTest(unittest.TestCase):
    def test_tampered_local_model_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / next(iter(cold_start.MODEL_FILES))
            first.parent.mkdir(parents=True)
            first.write_text("* changed model\n")
            with patch.dict(os.environ, {"CRYO_SHUTTLE_PDK": str(root)}):
                with self.assertRaisesRegex(ValueError, "PDK checksum mismatch"):
                    cold_start.copy_models(root / "simulation")

    def test_stuck_physical_bias_is_rejected(self):
        for far_read, error_read, expected_message in (
            (3.3, 0, "far terminal"), (0, 0.001, "guard tracking error"),
        ):
            with self.subTest(expected_message):
                with self.assertRaisesRegex(ValueError, expected_message):
                    cold_start.check_guard_bias([(1.65, 1e-16, far_read, error_read, 1.65)], 0, 0)

    def test_truncated_sweep_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "guard.dat").write_text("0.001 1e-16\n")
            with self.assertRaisesRegex(ValueError, "incomplete guard.dat"):
                cold_start.current_sweep(root, "guard.dat", 2, 201, 0.001, 0.01649)
