# Selection, readout and leakage budget

Decision 0001 proposes four force/sense pairs and one guard, shared by the structures in the [structure map](structure-map.md). No timing or leakage result for the complete selection network exists yet.

## Address and switching

Use ADDR[8:0] as the stable map code. ADDR[9] selects the physical replica for precision resistors and rings. Set MEAS_EN low, stop the oscillator, set the address, then assert MEAS_EN with the address stable before a rising clock edge. The decoder registers the address, opens every previous branch, waits one full selection-clock cycle, then enables one bank and one DUT and raises READY. Hold the address and stop CLK during a sensitive measurement. RST_N and deasserting MEAS_EN disconnect the buses and disable all rings. Reserved/dropped/cut codes and an unsupported replica selection stay disconnected with READY low.

Low-bank code 0 opens every branch. Codes 510 and 511 select open and short calibration structures with matched wiring. Code 510 ends in an unconnected DUT-side pad replica; code 511 joins the DUT-side force and sense contacts on the two Kelvin terminals with a short metal strap. Codes 494–509 are reserved. Neither calibration reference counts as a NIST DUT.

| Class | Terminals presented to the external instrument | Readout |
|---|---|---|
| Array and isolated FET | Pair 1 D, 2 G, 3 S, 4 B. The isolated module's X is a spare pad in the source drawing; keep unconnected. | Sweep gate or drain, acquire currents and actual DUT terminal voltages. For a substrate-tied device, hold body at VSS and vary source only within legal bias. Never force the body against the substrate. |
| MOS and overlap capacitors | Pair 1 gate, 2 common S/D, 3 body when separate. Where specified, short S/D/B at the DUT as on the source module. | Guarded small-signal C–V about a programmed DC bias. |
| Diodes and MIM | Pair 1 anode/top, 2 cathode/bottom, with well or substrate ties held at their permitted potentials. | Reverse-biased I–V and C–V for diodes, C–V for the MIM structures. Observe voltage polarity and terminal limits. |
| Precision resistors, metal and via chains | F1/S1 at the top end and F2/S2 at the bottom end. Independent sense contacts inside the force connections. | Determine R from sensed voltage difference and measured force current, reverse current to check offsets. |
| Ring oscillators | Pair 1 forces/senses VRO, pair 2 returns/senses local ground. RO_EN enables only the selected ring while MEAS_EN is active. | Count RO_OUT over a stated gate interval. Multiply by 1,024 to obtain the ring frequency. Record VRO and supply current. Require a valid digital crossing between VRO and the divider/readout rail before claiming a point. |

## Numerical acceptance

The NIST archive supplies sample magnitudes as context for the proposed budgets. A recorded zero has no finite relative error tolerance. For DC, take the smallest **nonzero absolute recorded output current**, including near-zero codes. These values reflect source instrumentation and do not establish the GF180 or instrument noise floor. The dedicated ISOFET worksheet has no separate measured I–V class in the archive, so it provisionally inherits the array-FET limit. For AC, the MDM outputs are capacitances in farads. The current column below is computed for the proposed GF test condition of 10 mV RMS at 10 kHz using (2πfV C). It is an equivalent signal, not a NIST current measurement. The oscillator files record output waveforms; its 1 µA minimum supply-current signal is a design assumption to verify. The proposed limits apply to the sum of all branches loading the selected terminal.

| Measurement class | Smallest reference signal | Proposed maximum absolute added current |
|---|---:|---:|
| FET drain, gate or body; isolated FET transfer | 10 fA measured / inherited | 5 fA |
| Area diode I–V | 10 fA | 5 fA |
| Area MOS C–V | 56.4188 fF → 35.45 pA | 3.5 pA |
| Overlap MOS C–V | 290.096 fF → 182.27 pA | 18 pA |
| MIM C–V | 66.5705 fF → 41.83 pA | 4.1 pA |
| Area diode C–V | 36.4592 fF → 22.91 pA | 2.2 pA |
| Precision poly R | 49.33 pA | 4.9 pA |
| Metal line R | 138.15 pA | 13 pA |
| Via-chain R | 747.07 pA | 74 pA |
| RO VRO current | 1 µA assumed | 100 nA |

Reproduce the current/capacitance minima and their file names with `python3 spec/reference_floors.py /tmp/nist-mpw5.zip`. The checksum is verified before the files are parsed. The ETest die and the separate room-temperature reference directory are excluded. For an individual DUT reporting a smaller resolved current than the reference signal, lower its budget so leakage stays below that DUT's smallest reported current. Any changed operating window or relaxed bound requires a subsequent decision.

## What must be measured before integration

At 25 °C, typical corner, a single unguarded open transmission gate (n/p 3.3 V devices, W=L=1 µm, finite junction area on both sides) delivers **68.20 fA** into a 0 V ideal instrument with its far terminal at 3.3 V in ngspice 47. With its far terminal also at 0 V it still delivers **63.53 fA**. Either absolute value exceeds the 5 fA FET/diode budget before further branches or pad leakage enter the circuit. Subtracting those cases would conceal junction and substrate current. This excludes that simple switch at that operating point.

Reproduce both readings with the `gf180mcuD` install from open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`:

```sh
scratch=$(mktemp -d)
cp spec/switch-reference.spice "$scratch/"
ln -s "$PDK_ROOT/gf180mcuD" "$scratch/pdk"
(cd "$scratch" && ngspice -b switch-reference.spice)
```

Evaluate banked isolation switches with an actively guarded intermediate node, separately biased wells where the PDK allows them, and the actual pad protection network. Guarding the intermediate node alone still leaves the measured-side junction current. Verify raw terminal loading against the limit, separately report fixture/pad leakage with the matched open, and report the residual after calibration. Include DC off current, on-drop against the Kelvin sense, AC parasitic/admittance after open/short calibration and settling after a code change. At each supplied GF180 model corner vary the selected terminal, unselected buses, inactive wells and supplies over the supported bias window. Use extracted parasitics and the worst bank population for the final comparison. Log the absolute instrument resolution and numerical tolerance behind any fA figure. Room-temperature model data cannot establish behaviour at liquid-helium temperatures.

If bank isolation, pad loading or measurement resolution prevents the target, record the failing terminal, bias and structure code in #2. A directly accessible reference may help diagnose that failure; it does not qualify a multiplexed DUT. At freeze, exclude unverified structures from the submitted map and keep their results visible. The complete-block signoff tracker keeps the original commitments until the operator disposes of them.
