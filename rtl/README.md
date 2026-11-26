# Characterization selector

`cryo_selector` receives the ten pad address bits, the selection clock, active-low reset, MEAS_EN and RO_EN. After enabling measurement, present the address before the rising edge. The first edge samples it with every switch open. The next edge enables the selection if the address is still stable. A changed sampled address restarts the blank cycle. Reset and MEAS_EN clear all switch controls immediately, including when the clock is stopped. Releasing either clear requires meeting the clock’s reset recovery and removal timing.

A DUT switch receives the intersection of `bank_enable[addr >> 4]` and `member_enable[addr & 15]`. These one-hot outputs and the decoded ring identity are registered. The primary and replica branches occupy separate banks. RO_EN gates only the selected ring. Bits 0–3 of `ring_enable` correspond to codes 482, 483, 484 and 487. Bits 4–7 are their replica placements. Set a bit in the synthesis parameter `CUT_PATHS` to disconnect its ten-bit address at freeze. Codes 510 and 511 select the primary open and short references.

The bit-level testbench reads [the structure map](../spec/structure-map.md) and checks the switch pins for all 1,024 addresses. It repeats the run with every path cut and with each of the ten address bits used as the cut mask. Those ten masks distinguish every address from every other one, including the two calibration references. It also pulses reset and deselect with the clock stopped and changes requests during the blank cycle. On a clean checkout install Python 3.12, Icarus Verilog (including `vvp`) and the pinned Python packages, then run from the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r verification/requirements.txt
python -m unittest discover -s verification -p test_selector.py
```

The Icarus RTL bench requires no PDK files. The integration target is GF180MCU-D, open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`. The switch devices, pad wiring, extracted timing and leakage require their own integration evidence.

## Ring readout and synthesis

The digital top is `cryo_char_ctrl`. The eight `ro_clk` inputs correspond to the eight `ring_enable` outputs in the same order. The analog interface must supply a buffered logic-domain edge from each oscillator. A level crossing from VRO that works over the measurement range still requires circuit and timing verification.

Each specimen has its own 10-bit counter. The first two rising edges after enabling synchronize the release of its local reset. The first rising edge of RO_OUT follows the 514th input rising edge, and successive rising edges are 1,024 input periods apart. Allow startup to settle before opening a frequency measurement window. Deasserting RO_EN, MEAS_EN or RST_N silences the output with both the oscillator and selection clocks stopped. A new selection starts with a fresh count.

Install Icarus with `vvp` and the Python pins, then run from the repo root.

```sh
python -m pip install -r signoff/klt-pin.txt -r rtl/synth-pin.txt
python rtl/regenerate.py --check
```

Omit `--check` to write `rtl/cryo_char_ctrl.gl.v`. KLT invokes the pinned WebAssembly Yosys with the GF180D 7-track, typical 25 °C, 3.30 V Liberty file. The runner verifies the Liberty and both Verilog model checksums against wafer.space PDK revision `ac7d8696de96a4d708e768b607ae37f02207a354`. Set `CRYO_SHUTTLE_PDK` to the local `gf180mcuD` directory for an offline replay. The top-level freeze-mask regression cuts primary 482 and replica 996 and checks that their opposite specimens still count. The standard cell models exercise both polarities of the divided clock, all eight channels, and restart while stopped. Timing closure, supply crossing and placed area require separate physical measurements.
