# Powered ASIG5V pad loading

This bench uses the complete foundry gf180mcu_fd_io__asig_5p0 SPICE cell from GF180D open_pdks f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7 on ideal powered rails. The meter holds ASIG5V at the stated voltage. No on-die switch, instrument noise, cable, package, board or secondary ESD element is present. The die plan requires those contributions in the physical qualification.

D2 runs from DVSS to ASIG5V and D3 from ASIG5V to DVDD. Each diode has four copies with 150 µm² junction area and 106 µm perimeter per copy. The other diode and the MOS capacitor are connected across the rails. The recorded signed clamp current delivered to the meter is I(D2) − I(D3). An independent pair of the exact pad-facing diode cards under the same bias reproduces both individual branch readings. An AC voltage of 10 mV at 10 kHz gives the pad capacitance from the imaginary source admittance.

| Diode corner, temperature, DVDD | ASIG5V | Signed clamp current | Pad capacitance |
|---|---:|---:|---:|
| Typical, 25 °C, 3.3 V | 0 V | +0.197 fA | 0.998 pF |
| Typical, 25 °C, 3.3 V | 1.65 V | −0.426 fA | 0.874 pF |
| Typical, 125 °C, 3.3 V | 0 V | +40.82 pA | 1.063 pF |
| Typical, 125 °C, 3.3 V | 1.65 V | −52.61 pA | 0.904 pF |
| Typical, 125 °C, 3.3 V | 3.3 V | −93.44 pA | 1.063 pF |
| Fast, 125 °C, 3.6 V | 3.6 V | −107.45 pA | 0.950 pF |

The [153 DC and AC points](measurements.csv) include 135 combinations of diode corner (typical, slow, fast), temperature (−40/25/125 °C), DVDD (3.0/3.3/3.6 V) and ASIG5V (0/25/50/75/100% DVDD). Capacitance spans 0.747–1.179 pF. The exposed pad has a bias-dependent capacitive baseline on every AC measurement. The figures above are compact-model predictions and establish no physical resolution.

The baseline solver uses GMIN = 10⁻¹⁸ S. Eighteen repeated points compare 10⁻¹² and 10⁻²¹ S. At typical/25 °C/0 V, 10⁻¹² S gives +3.300 pA, and 10⁻²¹ S gives +0.193 fA. The two smallest GMIN settings change the signed branch result by at most 0.0033 fA over the repeated conditions. The current read directly from the ideal voltage source differs from the diode-current sum by 2.0205 fA at its maximum over the baseline grid. Retain both in the CSV. Ngspice reports that the IKR effect is disabled for these diode models. Sub-fA transistor-model results, numerical cancellation and the two rails' opposite current directions cannot certify pad leakage, its drift or its noise.

Run with ngspice 46 and the pinned foundry install. The generator verifies four input digests, the native pad subcircuit and the open_pdks revision. It verifies measurements against the committed CSV by default.

```sh
python3 sim/pad-loading/measure.py --pdk "$PDK_ROOT/gf180mcuD" --ngspice ngspice --jobs 4
```
