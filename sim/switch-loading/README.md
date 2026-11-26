# Single-switch leakage and gate bias

The T4 control measures current delivered to a 0 V ideal instrument by one GF180D complementary transmission gate. The original finite source/drain geometry, model revision and solver tolerances come from the spec deck. The NMOS gate and body stay at 0 V and the PMOS well stays at 3.3 V. The experiment independently varies the PMOS gate. The 120 operating points cover TT, FF, SS, FS and SF at −40, 25 and 125 °C with both far-terminal voltages and four gate voltages. [Reference circuit](../../spec/switch-reference.spice) · [Signed measurements in amperes](measurements.csv)

| PMOS gate | Measured current at 0 V far terminal, typical 25 °C | At 3.3 V far terminal, typical 25 °C | Corners ≤5 fA at 0 V / 3.3 V far |
|---|---:|---:|---:|
| 3.30 V | 63.53 fA | 68.20 fA | 0/15 · 0/15 |
| 2.75 V | 9.56 fA | 354.77 pA | 0/15 · 0/15 |
| 2.20 V | 3.90 fA | 1.68 µA | 10/15 · 0/15 |
| 1.65 V | 3.73 fA | 10.60 µA | 10/15 · 0/15 |

At equal 0 V terminals and a 3.3 V PMOS gate, 59.81 fA of the 63.53 fA measured current is the modeled PMOS source-end gate-induced leakage. Reducing its gate bias to 1.65 V suppresses that component to 0.00050 fA. The measured-side junction current magnitude is 3.73 fA in both cases. At this reduced gate bias, a 3.3 V far terminal turns the PMOS on. The 125 °C results also show why an equal-terminal room-temperature observation cannot establish an operating range. The complete bank, pad, physical guard and measurement fixture need independent qualification. [T4 criteria](../../spec/selection-readout.md#fet-and-diode-dc-qualification)

Run the producer from the repository root using ngspice 47 and the Ciel GF180MCU-D variant from open_pdks revision `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`. It checks both source model files and compares all five recorded currents per point. The CSV retains each transistor component with the sign reported by ngspice. Use the aggregate terminal current for the target comparison.

```sh
python3 sim/switch-loading/measure.py --pdk "$PDK_ROOT/gf180mcuD"
```
