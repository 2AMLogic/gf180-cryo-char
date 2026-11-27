# Single-switch leakage and gate bias

The T4 control measures current delivered to a 0 V ideal instrument by one GF180D complementary transmission gate. The original finite source/drain geometry, model revision and solver tolerances come from the spec deck. The NMOS gate and body stay at 0 V and the PMOS well stays at 3.3 V. The experiment independently varies the PMOS gate. The 120 operating points cover TT, FF, SS, FS and SF at −40, 25 and 125 °C with both far-terminal voltages and four gate voltages. [Reference circuit](../../spec/switch-reference.spice) · [Signed measurements in amperes](measurements.csv)

| PMOS gate | Measured current at 0 V far terminal, typical 25 °C | At 3.3 V far terminal, typical 25 °C | Corners ≤5 fA at 0 V / 3.3 V far |
|---|---:|---:|---:|
| 3.30 V | 63.53 fA | 68.20 fA | 0/15 · 0/15 |
| 2.75 V | 9.56 fA | 354.77 pA | 0/15 · 0/15 |
| 2.20 V | 3.90 fA | 1.68 µA | 10/15 · 0/15 |
| 1.65 V | 3.73 fA | 10.60 µA | 10/15 · 0/15 |

At equal 0 V terminals and a 3.3 V PMOS gate, 59.81 fA of the 63.53 fA measured current is the modeled PMOS source-end gate-induced leakage. Reducing its gate bias to 1.65 V places that model component below the 0.01 fA solver absolute current tolerance. The measured-side junction current magnitude is 3.73 fA in both cases. At this reduced gate bias, a 3.3 V far terminal turns the PMOS on. The 125 °C results also show why an equal-terminal room-temperature observation cannot establish an operating range. With the nominal off controls and the far terminal at 3.3 V, the worst corner is FF at 125 °C: **42.28 pA**, including 39.30 pA NMOS drain current and 2.71 pA PMOS drain current in the device-model outputs. The complete bank, pad, physical guard and measurement fixture need independent qualification. [T4 criteria](../../spec/selection-readout.md#fet-and-diode-dc-qualification)

Run the producer from the repository root using ngspice 47 and the Ciel GF180MCU-D variant from open_pdks revision `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`. It checks both source model files and compares all nine recorded currents per point. The CSV retains each transistor component with the sign reported by ngspice. Use the aggregate terminal current for the target comparison.

```sh
python3 sim/switch-loading/measure.py --pdk "$PDK_ROOT/gf180mcuD"
```

## AC loading of inactive branches

The [AC control](measure_ac.py) drives the measured terminal at 10 mV RMS and 10 kHz. The ideal far terminal is held at 0 or 3.3 V DC and is AC-grounded. Zero, one and four identical parallel open switches use the exact transistor cards from the DC control. The [90 results](ac-loading.csv) cover five MOS process sections and three temperatures. Both real and imaginary currents enter the reported magnitude. Equivalent capacitance uses the imaginary current alone. An empty branch network gives zero at all 30 conditions. Four branches give four times the single-branch current at every condition.

At typical process, 25 °C and far terminal at 0 V, one branch draws 1.625 pA (2.586 fF), and four draw 6.500 pA (10.345 fF). The worst four-branch magnitude is 47.983 pA across this grid. These are raw added-current measurements on a deliberately unguarded control. The calibrated die and extracted production switch tree require their own tests. Both supported PDK revisions and the simulator commands are in the [simulation record](../README.md).

## Local mismatch of four open branches

The [seeded test](measure_mismatch.py) reuses the reference NMOS and PMOS geometry in four parallel branches. The GF180D transistor subcircuits apply their own local threshold and mobility mismatch to each instance. The harness selects the process corner, sets `sw_stat_global=0` and `sw_stat_mismatch=1`, and seeds ngspice **before** sourcing the devices. Each case uses 128 independent seed settings (1001–1128). The cases reuse those settings for paired comparisons. Within each draw the DC and AC analyses use the same instantiated devices. The output retains signed DC and both AC components for every draw. [384 samples](mismatch.csv)

| MOS corner / temperature | Instrument / far bias | Fixed signed DC | Upper bound on p95 absolute DC | Upper bound on p95 AC magnitude |
|---|---|---:|---:|---:|
| Typical, 25 °C | 0 / 0 V | +0.2541 pA | 0.2541 pA | 6.4999 pA |
| FF, 125 °C | 0 / 3.3 V | +169.1153 pA | 191.8637 pA | 54.7632 pA |
| FF, 125 °C | 3.3 / 0 V | −172.0483 pA | 195.2981 pA | 7.7554 pA |

For each quantity and condition, the 126th smallest of 128 samples is a distribution-free one-sided upper confidence bound for its 95th percentile (binomial coverage 95.74% for independent draws). Coverage applies separately to each column and condition. The signed current reverses at the hot bias swap. Typical equal-terminal DC is constant to the stored digits across seeds while AC changes. The inactive reference branches exceed the 5 fA design target even at the typical equal-terminal bias. The hot positive and negative cases also exceed the 10 fA reference-scale loading requirement. The four bare branches serve as a control for the planned bank. Its extracted topology, spatially correlated systematic offsets, pad mismatch and physical floor still need independent evidence.

Each case repeats its first seed exactly, toggles mismatch off at two seeds to recover one deterministic result, and disconnects all branches to check zero DC and AC. The ngspice 47 producer checks those controls before writing or comparing the CSV. Set `PDK` to a supported GF180D variant directory.

```sh
python3 sim/switch-loading/measure_mismatch.py --pdk "$PDK" --ngspice ngspice --jobs 4
```
