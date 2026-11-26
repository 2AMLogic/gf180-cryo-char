# Isolating the oscillator for VRO current measurements

The three layouts add a 0.42 × 0.28 µm NFET pass switch between each running oscillator and the extracted level shifter. A second NFET clamps the receiver to VSS during current measurements. Metal3 connects the original oscillator output to the pass device over 6.68 µm for 7T/9T and 6.66 µm for 12T. The physical boundary exposes `en, rx, read, read_b, vro, vss`. In the bench a GF180 7T inverter produces the complementary read control from the controller rail. Read mode and current-measurement mode are a proposed selector interface. Its distribution, switching sequence and assignment to the die controller remain open. [Generator and verification](physical.py)

Each integrated family matches the transistor schematic at 294 devices, 152 nets and six same-name pins with device width/length checks. All 148 NFET bodies connect to VSS and all 146 PFET bodies connect to VRO. Opening the middle of the new Metal3 segment produces 153 extracted nets and an LVS mismatch in every family. Native GF180D DRC reports zero markers across 763 rule categories in each family. The separate curated deck is clean on 7T/9T and retains the 440 findings inherited from the 12T OSU cells. [Physical measurements and layout hashes](verification.json) · [Original cores and OSU findings](../rings/README.md)

## Current measurement and readout

Each of 72 ngspice 46 transients uses the complete extracted oscillator, the extracted shifter and a routed divider clock tree with its twelve physical flip-flop loads. The bare control runs the original core with the receiver input grounded. For each paired measurement, subtract the grounded shifter's separately probed quiescent current from the control's VRO feed. Compare that bare oscillator current with the entire isolated candidate VRO feed over complete oscillator cycles. The signed difference includes switch loading, receiver quiescent current and changes in oscillator speed. [Bench](measure.py) · [All currents, receiver voltages and capture windows](measurements.csv)

| VRO at FF, −40 °C, 3.6 V controller | 7T added VRO current | 9T | OSU 12T |
|---|---:|---:|---:|
| 1.4 V | 0.02355 µA | 0.02517 µA | 0.04688 µA |
| 1.8 V | 0.05084 µA | 0.05476 µA | 0.09244 µA |
| 2.6 V | **0.11473 µA** | **0.12280 µA** | **0.19351 µA** |
| 3.6 V | **0.19489 µA** | **0.20712 µA** | **0.31713 µA** |

All three families exceed the proposed **0.100 µA** allowance at 2.6 and 3.6 V on this corner. At 1.8 V, 12T has just 0.00756 µA of modeled headroom. Halving the transient step at 1.4 and 3.6 V changes every paired result by less than 0.00041 µA. At 1.4 V the TT/25 °C and SS/125 °C points span 0.00699–0.03025 µA. A continuous operating range and measurement uncertainty still require qualification.

Read mode produces one divider toggle in each of 139 complete windows, matching the directly connected shifter control. The isolated receiver stays between −4.29 and +3.97 mV across the runs. Its shifter output remains below the controller logic threshold. At the high FF point the conducting NMOS delivers only 2.805–2.826 V peak to the shifter on the 3.6 V rail. The route between the new receiver port and shifter, mode-control distribution, pad, fixture and cryogenic operation remain outside these simulations. Current isolation above 1.8 V remains open for the December freeze.

## Replay

Use the GF180D Ciel installation identified in the [measurement manifest](measurements.manifest.json), ngspice 46, and a native KLayout binary on PATH. The physical replay compares regenerated GDS, schematics, extracted SPICE and receipts. The simulation replay verifies the pinned PDK input files and compares measured currents, timing, captures and paired current errors.

```sh
uv run --script design/ro-isolation/physical.py --pdk "$PDK_ROOT/gf180mcuD"
python3 design/ro-isolation/measure.py --pdk "$PDK_ROOT/gf180mcuD" --jobs 3
```
