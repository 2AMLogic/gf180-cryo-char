# Routed GF180D oscillator cores

Each core places one enable NAND, 142 inverters and one output buffer in twelve rows of twelve logic cells. The NAND and inverters form a 143-stage feedback loop. The 7- and 9-track rows include a foundry well-tap cell every four logic cells. The OSU 12-track cells contain their own taps. Adjacent OSU rows share implant strips, extended at the row ends to satisfy the foundry minimum width. [Structure map](../../spec/structure-map.md)

| Library | Specimen codes | Core outline including supply pins and fill | Ground capacitance in the extracted netlist |
|---|---|---:|---:|
| Foundry 7-track | 482 and its replica | 69.86 × 78.60 µm | 267.84 fF |
| Foundry 9-track | 483, 484 and their replicas | 69.86 × 92.08 µm | 293.62 fF |
| OSU 12-track | 487 and its replica | 68.60 × 132.10 µm | 391.42 fF |

Instantiate one independent core per specimen. The four public ports are `en`, `out`, `vro` and `vss`. Signal pins land on Metal3, with power on Metal2 at opposite corners of a 15 µm perimeter. Connect each output through the ring-to-divider level shifter. The raw GDS origin is inside the macro. The verification record gives each pin centre and bounding box in nanometres for die placement. [Coordinates, LVS and DRC](verification.json) · [Level shifter](../ro-crossing/README.md)

## Physical verification

For each stream, released KLT 0.9.2 matched all 149 nets, 292 transistors and four named pins against the pinned library SPICE. The comparison includes gate length and width. The foundry 5 V library wrappers use the 6 V MOS model cards under their documented W/L arguments. Extraction finds the 146 NMOS bodies on VSS and the 146 PMOS bodies on VRO. Cutting the returning Metal4 feedback track adds a 150th physical net and fails LVS in every family.

All three filled GDS streams pass the native GF180D deck with zero markers across the 763 categories listed for the complete variant-D run. The curated deck passes both foundry cores. On the OSU core it reports 294 N+ enclosure markers and 146 P+ spacing markers. Running the same two checks on the three original OSU library cells and weighting them by their instance counts reproduces those counts exactly. The native deck evaluates the well context at those taps. The curated result remains recorded as a violation. [Physical replay and library control](verify.py) · [Checked library digests](library-pins.json)

## Extracted readout

The ngspice bench connects the extracted core, the extracted level shifter, the routed divider clock-tree buffers, their SPEF wire capacitances and the twelve register loads for the selected port. It counts complete oscillator cycles after startup. At the fast −40 °C corner with VRO at 1.4 V and the controller at 3.6 V, all eight ports together captured **108/108** complete cycles. Applying the same extracted ring outputs directly to the divider on ports 0, 2 and 3 gave **0/43**. Holding enable low produced zero edges on all three cores. [Transients and unloaded controls](measurements.csv)

| Representative port | Frequency at 1.4 V / 3.6 V, fast −40 °C | Extra shared VRO current vs. unloaded | Extra VRO current after subtracting the shifter supply |
|---:|---:|---:|---:|
| 0, foundry 7-track | 13.405 MHz | 0.568 µA | 0.280 µA |
| 2, foundry 9-track | 14.115 MHz | 0.602 µA | 0.297 µA |
| 3, OSU 12-track | 25.702 MHz | 1.102 µA | 0.540 µA |

The residual exceeds the proposed 0.100 µA oscillator-current budget on each representative core. A DUT-only current measurement still requires isolation or a correction with validated uncertainty. The oscillator core, shifter and divider have distinct physical boundaries. The measurements exclude die-level interconnect between them and the real enable driver, pads and fixture. The extractor uses a 1 TΩ substrate reference and omits capacitance to the dummy-fill layers. No silicon or cryogenic floor has been measured. [Measurement requirements](../../spec/selection-readout.md)

At 3.6 V on both supplies, each representative port was simulated at five process corners and −40, 25 and 125 °C. All 356 complete cycles were captured. Each family's shortest period occurred at fast/−40 °C. The divider timing run uses shorter periods for all three families. It still has 65 unconstrained endpoints. [Divider timing report](../../flow/readout/timing.report.json) · [Measurement inputs and results](measurements.manifest.json)

| Library | Simulated range at 3.6 V | Shortest observed period | Divider timing constraint | Captured cycles |
|---|---:|---:|---:|---:|
| Foundry 7-track | 21.11–54.14 MHz | 18.470 ns | 12.0 ns | 89/89 |
| Foundry 9-track | 22.51–57.37 MHz | 17.429 ns | 12.0 ns | 95/95 |
| OSU 12-track | 42.07–80.64 MHz | 12.401 ns | 9.5 ns | 172/172 |

## Replay

Use the gf180mcuD variant of open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`, ngspice 46, and KLayout CLI on PATH. The physical scripts pin KLT 0.9.2 and the KLayout 0.30.14 Python binding. The native DRC record was produced with KLayout CLI 0.30.12. Set `NGSPICE` to select the simulator executable. Run from this directory.

```sh
uv run --script generate.py --pdk "$PDK_ROOT/gf180mcuD" --out /tmp/cryo-ring-rebuild
uv run --script verify.py --pdk "$PDK_ROOT/gf180mcuD"
python3 measure.py --pdk "$PDK_ROOT/gf180mcuD" --port 2
```

The generator verifies the source GDS, LEF and SPICE digests. It also verifies the SHA-256 of the shared GF180 fill script before using it. Pass `--fill-script /path/to/fill_partitions.py` for an offline build. The fill receipts identify the intermediate layout before its fill cell receives its family-specific name. The verification record identifies the final GDS by digest. Compare the three regenerated GDS streams, schematics and fill reports with the committed files. `verify.py` repeats extraction and compares the simulated SPICE byte for byte. Omit `--port` to rerun the entire measured grid. [Pinned fill generator](https://github.com/2AMLogic/gf180-efuse-otp/blob/5ff12fe481ca9c52c653896f298aea3241184c51/layout/fill_partitions.py)
