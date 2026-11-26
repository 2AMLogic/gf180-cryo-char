# Selection, readout and leakage budget

Decision 0001 proposes four force/sense pairs and one guard, shared by the structures in the [structure map](structure-map.md). No timing or leakage result for the complete selection network exists yet.

## Address and switching

Use ADDR[8:0] as the stable map code. ADDR[9] selects the physical replica for precision resistors and rings. Set MEAS_EN low, stop the oscillator, set the address, then assert MEAS_EN with the address stable before a rising clock edge. The decoder registers the address, opens every previous branch, waits one full selection-clock cycle, then enables one bank and one DUT and raises READY. Hold the address and stop CLK during a sensitive measurement. RST_N and deasserting MEAS_EN disconnect the buses and disable all rings. Reserved/dropped/cut codes and an unsupported replica selection stay disconnected with READY low.

Low-bank code 0 opens every branch. Codes 510 and 511 select open and short calibration structures with matched wiring. Code 510 ends in an unconnected DUT-side pad replica; code 511 joins the DUT-side force and sense contacts on the two Kelvin terminals with a short metal strap. Codes 494–509 are reserved. Neither calibration reference counts as a NIST DUT.

| Class | Terminals presented to the external instrument | Readout |
|---|---|---|
| Array and isolated FET | Pair 1 D, 2 G, 3 S, 4 B. The isolated module's fifth source label is X. Its function is unspecified in the workbook and slide 7; leave it unconnected unless a source-backed revision assigns it. | Sweep gate or drain, acquire currents and actual DUT terminal voltages. For a substrate-tied device, hold body at VSS and vary source only within legal bias. Never force the body against the substrate. |
| MOS and overlap capacitors | Pair 1 gate, 2 common S/D, 3 body when separate. Where specified, short S/D/B at the DUT as on the source module. | Guarded small-signal C–V about a programmed DC bias. |
| Diodes and MIM | Pair 1 anode/top, 2 cathode/bottom, with well or substrate ties held at their permitted potentials. | Reverse-biased I–V and C–V for diodes, C–V for the MIM structures. Observe voltage polarity and terminal limits. |
| Precision resistors, metal and via chains | F1/S1 at the top end and F2/S2 at the bottom end. Independent sense contacts inside the force connections. | Determine R from sensed voltage difference and measured force current, reverse current to check offsets. |
| Ring oscillators | Pair 1 forces/senses VRO, pair 2 returns/senses local ground. RO_EN enables only the selected ring while MEAS_EN is active. | Count RO_OUT over a stated gate interval. Multiply by 1,024 to obtain the ring frequency. Record VRO and supply current. Require a valid digital crossing between VRO and the divider/readout rail before claiming a point. |

## Numerical acceptance

The smallest nonzero FET and diode DC readings in the NIST archive are 10 fA. This is the reference instrument's recorded increment near zero. Use 5 fA as the design target for the magnitude of the total signed switch current delivered to one selected terminal by all branches together over the predeclared supported bias conditions. The pre-freeze design screen includes all five supplied MOS process corners at −40, 25 and 125 °C. Use the published worst value over that grid and report the temperature, voltage and bias envelope of any narrower physical claim. Cryogenic sensitivity requires measurements at the claimed temperature. The GF180 measurement range comes from the physical controls below. Isolated FETs use the same qualification because the archive has no separate measured I–V class for that worksheet.

For AC the archive reports capacitance. The equivalent current below uses the proposed GF test conditions of 10 mV RMS at 10 kHz and the relation 2πfVC. The 1 µA oscillator supply signal is a design assumption. The table covers aggregate mux loading at one selected terminal.

| Measurement class | Reference magnitude or increment | Proposed absolute added current |
|---|---:|---:|
| FET drain, gate or body, including isolated FET | 10 fA reference increment | 5 fA design target |
| Area diode I–V | 10 fA reference increment | 5 fA design target |
| Area MOS C–V | 56.4188 fF → 35.45 pA | 3.5 pA |
| Overlap MOS C–V | 290.096 fF → 182.27 pA | 18 pA |
| MIM C–V | 66.5705 fF → 41.83 pA | 4.1 pA |
| Area diode C–V | 36.4592 fF → 22.91 pA | 2.2 pA |
| Precision poly R | 49.33 pA | 4.9 pA |
| Metal line R | 138.15 pA | 13 pA |
| Via-chain R | 747.07 pA | 74 pA |
| RO VRO current | 1 µA assumed | 100 nA |

Reproduce the current/capacitance minima and their file names with `python3 spec/reference_floors.py /tmp/nist-mpw5.zip`. The checksum is verified before the files are parsed. The ETest die and the separate room-temperature reference directory are excluded. For classes with a numerical acceptance bound, apply the tighter limit if the DUT has a smaller resolved signal. A change to an agreed operating window or acceptance bound requires a subsequent decision.

## FET and diode DC qualification

1. **Declare the claim before collecting DUT data.** Record the terminal and structure codes, smallest claimed absolute current `I_min`, sign, terminal and inactive-branch bias ranges, temperature, bank population, guard setting, instrument range, settling time, integration time and averaging. Evaluate each configuration that the claim covers. Retain the original range and result if a narrower range is later proposed.
2. **Measure the floor.** Record repeated instrument/fixture blanks with the guarded input terminated as it will be probed. Separately characterize the powered pad and its actual secondary protection on a pad-only structure or a demonstrably equivalent coupon. Sweep pad and rail bias, temperature and time. Record the signed raw current, its change between matched pads and, for AC, the complex open admittance. Repeat through the biased pad and matched on-die open (code 510) with the same bank loading as the DUT. Attribute the difference to the selected route only within the measured mismatch and drift uncertainty. Use the short (511) to check continuity and settling. Bracket the DUT series with blanks to measure drift. Use separate blanks to fit and to validate any offset correction. Report raw signed currents and the upper 95% prediction bound on the absolute corrected matched-blank reading, `F95`, for one result using the declared acquisition procedure. Document the repeat count, time span and method supporting that coverage, including drift or correlated samples.
3. **Verify current recovery and uncertainty.** Apply an independently calibrated current at the DUT side, or through a demonstrated equivalent replica of the complete selected path. Exercise the smallest proposed current and each claimed polarity. Include the reference source, repeatability, quantization, offset correction, pad mismatch, drift and residual mux error in the uncertainty budget once each, with correlations where applicable. Report expanded uncertainty `U95`, its coverage factor and its basis. The recovered current must have the expected sign and agree with the calibrated input within their combined 95% uncertainty. An external pad injection that bypasses the switches qualifies only the fixture and pad. [NIST guidance on expanded uncertainty](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-6-expanded-uncertainty)
4. **Decide the range and report each point.** To qualify the declared range, require `F95 < I_min` and an upper bound on worst-case absolute raw aggregate mux loading below `I_min`. At the smallest injected current, and for each DUT reading reported as resolved, require `abs(I_corrected) > F95` and a 95% current interval that excludes zero. Report the separate raw pad/clamp and switch bounds at the same operating point and the total raw current before correction. Carry any pad-background subtraction, mismatch and drift into F95 and U95 using independent physical blanks. A model-only subtraction or an unmeasured pad/protection background leaves the range pending. A precision claim must also meet its stated absolute or relative uncertainty. Record readings below the qualified range as unresolved with the measured floor and uncertainty. Record a 5 fA design-target miss independently, even when a larger current range qualifies.

The reference-scale detection claim has a fixed smallest test current of **10 fA** in each claimed polarity. To claim it, report the physical tests above at 10 fA. If these fail or are unavailable, publish that claim as failed or pending and retain the original 5 fA raw target and its outcome. A laboratory may characterize a larger predeclared range and publish the actual numerical lower endpoint, raw-loading bound, floor and uncertainty. Counting that range in place of the reference-scale commitment for a release or a Bronze grant requires a separate numeric spec decision, independent review and operator approval.

At the December freeze, publish the extracted mux bounds, the raw controls, and the status of each proposed range. A physical floor established on a representative coupon must identify how its pad, switch path, loading and fixture match. If physical controls are unavailable, label the range **pending measurement**. Simulations support design review and cannot establish the pad-and-fixture floor or qualify a cryogenic temperature.

## What must be measured before integration

At 25 °C, typical corner, a single unguarded open transmission gate (n/p 3.3 V devices, W=L=1 µm, finite junction area on both sides) delivers **68.20 fA** into a 0 V ideal instrument with its far terminal at 3.3 V in ngspice 47. With its far terminal also at 0 V it still delivers **63.53 fA**. Both absolute values miss the 5 fA FET/diode design target before other branches and the pad enter the circuit. Their difference is the change with far-terminal bias. The 63.53 fA baseline remains in the terminal current. At equal 0 V terminals, the pinned BSIM model reports 59.81 fA PMOS gate-induced source leakage (IGISL) and a 3.73 fA magnitude source/body junction contribution. IGISL is the source-side counterpart of gate-induced drain leakage. The two internal ends of this symmetric device each report a gate-induced term. Use only the term associated with the measured terminal in its current balance.

Holding the PMOS well at 3.3 V and reducing its gate from 3.3 V to 1.65 V at equal 0 V terminals lowers total loading from 63.53 to 3.73 fA in this typical, 25 °C simulation. The same fixed gate bias with the far terminal at 3.3 V delivers **10.60 µA** into the instrument, as the high terminal turns on the PMOS channel. Intermediate gate bias requires tracking of both switch terminals, with off-state and transition checks across the claimed range. At equal zero terminals and 1.65 V gate bias, ten of fifteen modeled process/temperature points meet 5 fA. The worst is 160.77 fA. At the normal 3.3 V gate bias all fifteen miss at either far-terminal voltage. At FF, 125 °C and a 3.3 V far terminal, the worst raw loading is **42.28 pA**. The BSIM NMOS drain current is 39.30 pA and PMOS drain current 2.71 pA. The cold/equal-terminal gate-induced explanation cannot be carried over to this hot, unequal-terminal state. These are single-switch negative controls. [120-point bias and PVT record](../sim/switch-loading/README.md)

Reproduce both readings with the `gf180mcuD` install from open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`:

```sh
scratch=$(mktemp -d)
cp spec/switch-reference.spice "$scratch/"
ln -s "$PDK_ROOT/gf180mcuD" "$scratch/pdk"
(cd "$scratch" && ngspice -b switch-reference.spice)
```

Evaluate banked isolation switches with an actively guarded intermediate node, separately biased wells where the PDK allows them, and the actual pad protection network. Sweep the gate-to-terminal electric field as well as guard-node voltage, well bias, device width, junction area and temperature. Check both extremes of the far terminal for channel conduction. Extract the selected path and include the simultaneous contributions of its inactive branches. Sweep raw terminal loading, record the class target or limit, and report the residual after calibration alongside the fixture and matched-open records. Include DC off current, on-drop against the Kelvin sense, AC parasitic/admittance after open/short calibration and settling after a code change. At each supplied GF180 model corner vary the selected terminal, unselected buses, inactive wells and supplies over the supported bias window. Use extracted parasitics and the worst bank population for the final comparison. Log the absolute instrument resolution and numerical tolerance behind any fA figure. Room-temperature model data cannot establish behaviour at liquid-helium temperatures.

If bank isolation, pad loading or measurement resolution prevents the target, record the failing terminal, bias and structure code in #2. A directly accessible reference may help diagnose that failure; it does not qualify a multiplexed DUT. At freeze, exclude unverified structures from the submitted map and keep their results visible. The complete-block signoff tracker keeps the original commitments until the operator disposes of them.
