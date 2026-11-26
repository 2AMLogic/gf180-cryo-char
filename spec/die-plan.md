# Full-slot die and pad assignment

This is the physical interface proposed in decision 0001. Use wafer.space project-template commit `d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c`, `SLOT=1x1`, the default foundry `gf180mcu_fd_io` pads and `gf180mcu_fd_sc_mcu7t5v0` control cells. Select the 3.3 V operating point and timing libraries. VDD and DVDD are both 3.3 V nominal; the foundry I/O library connects those domains. The acceptance sweep for control logic is at the available 3.00/3.30/3.60 V library points. Measurement pads stay within the powered I/O rails. The sensing circuitry has no externally applied 5 V rail in this proposal. The Run 3 GF180MCU-D process has five routing metals, a 1.1 µm top metal and 2 fF/µm² MIM. [Template](https://github.com/wafer-space/gf180mcu-project-template/tree/d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c) · [Slot configuration](https://github.com/wafer-space/gf180mcu-project-template/blob/d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c/librelane/slots/slot_1x1.yaml) · [Process option](https://github.com/wafer-space/gf180mcu/blob/ac7d8696de96a4d708e768b607ae37f02207a354/gf180mcuD/.config/nodeinfo.json)

The outline is **3,932 × 5,122 µm**, origin (0,0). The template core box is (442,442)–(3490,4680) µm, or 3,048 × 4,238 µm. Preserve the seal ring, chip identification, required marks, all bondpad centres and all 18 power/ground pads. Only seven existing north-side signal positions change pad type, from bidirectional digital to the template's `asig_5p0` analog pad. That gives nine analog, 33 bidirectional and twelve general input pads, plus dedicated clock/reset and the eighteen supply pads: **74 bond positions**. Keep the resulting bidirectional indices contiguous, 0 through 32. The package/instrument fixture must match these signal roles.

| Template bond position | New port | Use at the instrument |
|---|---|---|
| North analog[0], analog[1] | F1, S1 | Force and Kelvin sense of terminal 1. |
| North bidir[39], bidir[38] → analog[2:3] | F2, S2 | Force and Kelvin sense of terminal 2. |
| North bidir[37], bidir[36] → analog[4:5] | F3, S3 | Force and Kelvin sense of terminal 3. |
| North bidir[35], bidir[34] → analog[6:7] | F4, S4 | Force and Kelvin sense of terminal 4. |
| North bidir[33] → analog[8] | GUARD | Externally driven guard/shield for the selected sensitive bus, current-limited and inside the rails. |
| South clk_pad, rst_n_pad | CLK, RST_N | Selection clock and active-low reset. |
| West inputs[0:9] | ADDR[0:9] | Binary selection and replica bit. |
| West inputs[10], inputs[11] | MEAS_EN, RO_EN | Enable analog routing and oscillator drive, respectively. |
| South bidir[0] | RO_OUT | Divided digital frequency sense output. |
| South bidir[1] | READY | Digital readback that the new selection has latched and the blank cycle has elapsed. |
| Remaining bidir[2:32] | NC | Output disabled, pull-up/down disabled, no instrument forcing; retain bond locations. |
| dvdd_pads[0:5], vdd_pads[0:1] | DVDD, VDD | Force nominal 3.3 V at all supply pads. |
| dvss_pads[0:7], vss_pads[0:1] | DVSS, VSS | Force common ground at all return pads. |

Sense connects to the DUT side of its force switch through a separate branch. Keep sense traces away from the decoder and oscillator. The north measurement edge feeds guarded banks, Kelvin metal/via structures and direct connection calibration standards near that edge. Place oscillator banks separately from the high-impedance analog buses. Place and route the digital decoder outside those banks. The final placement must reconcile every code, terminal and reference in the netlist with the pad above.

## Powered measurement pads and protection

Use the template's gf180mcu_fd_io__asig_5p0 for the nine in-rail analog connections. D2 and D3 connect the measurement node directly to DVSS and DVDD. Their reverse leakage and junction capacitance reach the instrument with every mux switch open. An external driven guard can reduce fixture leakage. Bank sizing can reduce switch loading. Both pad junctions remain connected. On the pinned GF180D model their signed sum reaches −107.45 pA at FF/125 °C with ASIG5V = DVDD = 3.6 V. The standalone pad capacitance spans 0.747–1.179 pF in the 10 kHz sweep. [Pad model, signed currents and numerical controls](../sim/pad-loading/README.md).

The antifuse sibling proposes a bare pad for the externally driven high-voltage programming electrode because its voltage forward-biases a standard pad clamp. Cryo uses powered rails and keeps the measurement potential within DVSS–DVDD. This removes the high-voltage forward-conduction requirement. Reverse leakage, pad-to-pad mismatch and the capacitive background still limit low-current and AC claims. The standard cell preserves the shuttle pad positions and primary protection while T4 requires a measured floor. If a usable range cannot be established, record the affected measurement as pending or failed. A different pad or release range needs independent review and operator ratification before integration. [Antifuse program-pad decision](https://github.com/2AMLogic/gf180-antifuse/blob/0c924b7baf4b39af9b8f315063251db40d18f4ac/spec/hv-pad-protection-decision.md).

GlobalFoundries describes this analog pad for thick-gate circuits and requires secondary ESD protection near the internal devices. Include that protection, its resistance, leakage and capacitance in the assembled path, especially where a measurement reaches a thin gate. Record the actual clamp and series element geometry, confirm protection and allowable force/bias for each terminal, and repeat DC and AC extraction with those elements and the package/pad routing. This is an open integration check for the December 9 freeze. The published library input-leakage specification of ±5 µA covers 4.50–5.50 V GPIO conditions. It supplies no fA leakage bound for this pad at 3.3 V. [Foundry analog pad guidance](https://gf180mcu-pdk.readthedocs.io/en/latest/IPs/IO/gf180mcu_fd_io/analog.html) · [Electrical characterization conditions](https://gf180mcu-pdk.readthedocs.io/en/latest/IPs/IO/gf180mcu_fd_io/electrical.html).

Issue #4 owns the empty-die precheck and subsequent integration runs on the shuttle PDK. The earlier example-GDS check exercised the upstream counter design. The project die requires its own full precheck log, GDS hash and release. Freeze December 9, 2026; deliver the clean GDS to the community slot holder by December 16. Record each cut under its original select code.
