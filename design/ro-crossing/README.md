# Ring-to-divider level shifter

With a 1.4 V oscillator driving a 3.6 V controller, the direct connection captured **0/158** complete cycles at the fast −40 °C corner. Inserting the extracted six-transistor `efuse_ls` between each ring output buffer and its routed clock tree recovered **158/158**. The shifter uses an input inverter on the ring supply and a cross-coupled stage on the controller supply. The published readout-controller GDS has separate clock input ports for the eight instances. [Direct control and controller layout](../../flow/readout/README.md)

## Die connections and measurement burden

| Cell port | Connection |
|---|---|
| `in` | Selected specimen's buffered oscillator output |
| `out` | Its corresponding digital macro port `ro_clk[i]` |
| `vdd33` | Low-side inverter supply, biased at the ring voltage |
| `vprog` | Controller supply, 3.0–3.6 V in these measurements |
| `vss` | Common return |

Use one cell per channel. The physical rails retain their eFuse library names. The cell bounding box is 18.29 × 19.92 µm, with its lower-left corner at (−1.20, −1.71) µm in the delivered GDS. Keep the two positive supply nets separate during integration. The transistor-level layout comparison matches all five public pins, seven nets and six devices. A Metal4 bridge between the supply probes reduces the net count to six and fails LVS. The extracted SPICE includes 24 resistors, seven ground capacitors and eight coupling capacitors. The substrate capacitance uses the extractor's default 1 TΩ DC reference. [GDS](efuse_ls.gds) · [Schematic](efuse_ls.spice) · [Extracted SPICE](efuse_ls.pex.spice) · [LVS](lvs.report.json) · [Extraction](extract.report.json)

The current drawn from `vdd33` enters the VRO ammeter reading when both share a feed. At the fast split-supply corner, the level shifter alone drew **0.447–0.705 µA** from that feed. Even at slow 125 °C and 1.4 V / 3.0 V, it drew 0.132–0.297 µA. These exceed the proposed **0.100 µA** loading budget. Twelve additional simulations disconnect the shifter input from the oscillator buffer and leave that buffer unloaded. Using the same family, PDK, time step and temperature as each routed run gives the current added by the receiver. The shared-feed column is the difference between the loaded and unloaded VRO current. The separate-feed column subtracts the measured low-side shifter supply current from that difference. Each range covers all eight channels. [Unloaded oscillator controls](unloaded.csv) · [Receiver measurements](measurements.csv)

| Process and temperature | Ring / controller | Shared feed, added µA | Separate feed, added µA |
|---|---|---:|---:|
| Typical, 25 °C | 1.4 V / 3.3 V | 0.477–0.880 | 0.238–0.431 |
| Fast, −40 °C | 1.4 V / 3.6 V | 0.890–1.388 | 0.443–0.683 |
| Slow, 125 °C | 1.4 V / 3.0 V | 0.262–0.580 | 0.130–0.284 |
| Fast, −40 °C | 3.6 V / 3.6 V | 9.377–11.489 | 4.221–5.447 |

All 32 comparisons exceed the proposed 0.100 µA budget even with separately metered shifter power. These points support frequency readout. A DUT-only current claim still needs a receiver-disconnected measurement mode or a validated loading correction with uncertainty below budget. The assembled die must also account for the enable crossing, interconnect, pads and fixture. [Measurement requirements](../../spec/selection-readout.md)

## Receiver measurements

The ngspice 46 bench includes the gated 143-stage ring, its output buffer, the extracted shifter, the physical clock-tree buffers, twelve register loads per port and the four clock-net capacitances from the controller SPEF. One register per port is toggle-connected. The measurement counts full ring cycles with exactly one register transition after startup. Zero-volt sense sources measure current into the two shifter supply pins independently. The total VRO current includes the low-side shifter current and the ring's output drive. [Measured points](measurements.csv) · [Receiver bench](../../sim/readout/routed_ring.py)

| Process and temperature | Ring / controller | Ports | Captures / complete cycles |
|---|---|---:|---:|
| Typical, 25 °C | 1.4 V / 3.3 V | 8 | 82/82 |
| Fast, −40 °C | 1.4 V / 3.6 V | 8 | 158/158 |
| Slow, 125 °C | 1.4 V / 3.0 V | 8 | 72/72 |
| Fast, −40 °C | 3.6 V / 3.6 V | 8 | 52/52 |
| FS, −40 °C | 1.4 V / 3.6 V | 3 | 27/27 |
| SF, 125 °C | 1.4 V / 3.0 V | 3 | 56/56 |

The representative ports 0, 2 and 3 exercise the 7-, 9- and 12-track rings. At fast −40 °C and 1.4 V / 3.6 V, reducing the maximum step from 40 ps to 10 ps preserved 62/62 captures across those ports. The schematic version also captured 62/62. The wafer.space model files reproduced 34/34 with the two foundry-family ports. The OSU 12-track ring uses the open_pdks library. Each PDK run checks the model file digests. These are circuit simulations of the listed operating points. Die routing, physical pin positions of the ring outputs, cryogenic behavior and yield remain open. [Model pins](../../sim/readout/ring_inputs.json)

## Reproduction

The GDS and schematic are isolated from the GF180 eFuse project at `5ff12fe481ca9c52c653896f298aea3241184c51`, under the same Apache 2.0 license. The verifier hashes both upstream inputs, exports only the cell hierarchy without timestamps, and compares the schematic text and GDS byte for byte. It also extracts the shipped stream on the GF180D 11K stack, compares each gate, body, diffusion connection, length and width, and checks that the resulting SPICE is byte-identical to the simulated file. [Upstream layout](https://github.com/2AMLogic/gf180-efuse-otp/blob/5ff12fe481ca9c52c653896f298aea3241184c51/layout/efuse_otp_array.gds) · [Upstream schematic](https://github.com/2AMLogic/gf180-efuse-otp/blob/5ff12fe481ca9c52c653896f298aea3241184c51/design/efuse_otp_array.spice)

Set `PDK_ROOT` to the directory containing the gf180mcuD variant at open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`. Run these commands from this directory.

```sh
uv run --script verify.py --efuse-checkout /path/to/pinned/gf180-efuse-otp
python replay.py --pdk-source open_pdks --pdk "$PDK_ROOT/gf180mcuD"
python replay.py --pdk-source wafer-space --pdk /path/to/shuttle/gf180mcuD
```

Omit `--efuse-checkout` for extraction, LVS and the physical fault controls using the shipped files alone. Add `--port 2` to replay one port's measurements. The replay checks integer capture counts exactly and each recorded analog measurement to 0.5% relative or 0.001 in the recorded units. Set `NGSPICE` when the ngspice 46 executable is outside PATH.

The curated deck returned zero markers across 58 checked rules. The native deck reported one density finding for each of DCF.1b, PL.8, M1.4 through M5.4, and MT.3 on the isolated cell. Recheck these on the assembled die. The cell covers one receiver of the analog partition. Its reports leave the complete analog-partition layout, verification and Bronze criteria open. [Curated DRC](drc-curated.json) · [Native DRC](drc-native.json)
