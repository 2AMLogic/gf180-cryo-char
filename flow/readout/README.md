# GF180D routed readout controller

The integration input for the die floorplan is [cryo_char_ctrl.gds](cryo_char_ctrl.gds), with port names, coordinates and supply nets in the [routed DEF](cryo_char_ctrl.def). The controller occupies **244.42 × 244.42 µm** including its margin. The selector, eight divide-by-1,024 channels and their reset logic occupy a 49,172.5 µm² core. This build uses the default 1,024-bit `CUT_PATHS=0` mask in the mapped [controller](../../rtl/cryo_char_ctrl.gl.v). Changing a freeze mask requires a new synthesis and route.

The [route record](route.json) binds the 576-cell source netlist, request, DEF and GDS by SHA-256. Detailed routing returned zero markers. The DEF contains 2,766 placed components, including 435 taps, with VDD and VSS special nets. Physical clock-tree synthesis reached 64 sinks on `clk`. The eight `ro_clk` inputs use ordinary signal routing. Full clock-tree coverage, signal and supply LVS, supply ERC and die-level density/precheck remain open. [Readout layout tracker](https://github.com/2AMLogic/gf180-cryo-char/issues/17) · [Multi-clock CTS](https://github.com/2AMLogic/klayout-tools/issues/7945) · [Die handoff](https://github.com/2AMLogic/gf180-cryo-char/issues/4)

## Reproduce the layout

Use Python with `klayout-tools==0.9.2`, the KLayout Python package 0.30.14, OpenROAD `26Q3-1510-g6cb3f2b704` on PATH, and `PDK_ROOT` containing gf180mcuD at open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`. The route used the linux/amd64 image `openroad/orfs@sha256:bb7f31697fb8466ab61852fc796376cc16d9df38f762ccb733218b8a5e55824b`. A containerized OpenROAD needs the working directory, resolved temporary directory and PDK accessible at the same absolute paths as on the host. From the repository root:

```sh
python flow/reproduce.py
python flow/reproduce.py --reroute
```

The full replay checks the clock-tree log and physical metrics, then compares the new DEF and the timestamp-free 1 nm GDS with the published bytes. Conversion from the router’s 0.5 nm units compares the merged drawn masks by XOR on every layer and compares cell placements and labels on their original grid. Native DRC used the KLayout 0.30.13 executable. The [curated run](drc-curated.json) found zero markers across 72 checked rules. The [native DRC run](drc-klayout.json) found eight density markers on the macro alone, one each for DCF.1b, PL.8, M1.4 through M5.4, and MT.3. Recheck after die assembly and fill.

```sh
macro=flow/readout/cryo_char_ctrl
klt drc "$macro.gds" --pdk gf180mcuD --deck gf180mcu --top cryo_char_ctrl --engine curated --format json
klt drc "$macro.gds" --pdk gf180mcuD --top cryo_char_ctrl --engine klayout --format json
```

## Divider clocks and supply crossing

The [ngspice bench](../../sim/readout/ring_clock.py) instantiates one gating NAND, 142 inverters and the output buffer from each selected cell family. The primary NIST codes 482, 483, 484 and 487 drive ports 0 through 3. The corresponding replicas drive ports 4 through 7. Codes 483 and 484 share a 9-track electrical model. Routing differences between specimens remain to be extracted.

Each clock port drives twelve 7-track DFF clock pins in the DEF. The nominal 72 fF load combines the largest extracted port wire capacitance (31.529683 fF) with twelve 3.346 fF typical Liberty clock pins. The split-supply control replaces the lumped pin load with twelve transistor-level DFFs, monitors one toggle-connected DFF, and retains the 31.529683 fF wire load.

| GF180 ring family | Typical, 25 °C, 3.3 V at 120 ps step | Fast corner, −40 °C, 3.6 V at 0.625 ps step | Period used in STA |
|---|---:|---:|---:|
| Foundry 7-track | 43.59 MHz | 81.13 MHz | 12.0 ns |
| Foundry 9-track | 45.60 MHz | 80.65 MHz | 12.0 ns |
| OSU 12-track | 63.62 MHz | 101.09 MHz | 9.5 ns |

The [71 simulation cases](ring-clock-measurements.csv) record loads, supplies, process, temperature, timestep, run length and receiver transitions. The [24 timestep controls](ring-step-control.csv) used a 110 ns transient at the fast corner with the 72 fF load. The 5 ps run gave a shortest 12-track period of 9.911 ns. Finer steps yielded 9.897 ns at 2.5 ps and 9.892 ns at 0.625 ps. The timing constraints keep at least 2% period margin against the finest measured case in each family. Internal wire-load cases add 1 or 3 fF per stage. These are schematic models at specified PVT corners. Die routing, device variation and cryogenic operation require separate characterization.

With VRO at 1.4 V and the receiver at 3.3 V, the typical 7-track ring oscillated at 11.37 MHz while the DFF captured zero of eight complete cycles, at both 120 ps and 40 ps timesteps. At 1.65 V the receiver toggled in every measured window at the tested points. This leaves voltage translation and its qualified supply range open for the die. ngspice 46 and the [model checksums](../../sim/readout/ring_inputs.json) identify the open_pdks build used here. The [eight independent PDK controls](ring-shuttle-controls.csv) repeat the nominal and fast runs and both split-supply cases with the wafer.space files. Its 7- and 9-track families reproduced the open_pdks results at the same 5 ps timestep and both missed all eight measured cycles at 1.4 V. Use `--pdk-source wafer-space --pdk /path/to/shuttle/gf180mcuD` for those cases. The pinned wafer.space bundle uses different transistor-model files and lists foundry 7- and 9-track libraries. The OSU 12-track source needs a separately pinned integration view. [Shuttle PDK](https://github.com/wafer-space/gf180mcu/tree/ac7d8696de96a4d708e768b607ae37f02207a354/gf180mcuD/libs.ref)

```sh
python sim/readout/ring_clock.py 12t ff -40 3.6 --pdk "$PDK_ROOT/gf180mcuD" --step-ns 0.005 --duration-ns 110
python sim/readout/ring_clock.py 7t typical 25 1.4 --pdk "$PDK_ROOT/gf180mcuD" --logic-supply 3.3 --load-ff 31.529683 --duration-ns 950
```

## Extract and time the routed macro

Generate the SPEF from the committed GDS with the pinned extractor revision below. Its DEF identifier escaping is required by the OpenROAD reader. The [extraction record](extraction.json) binds its GDS, DEF and output SPEF. It recognized 7,506 devices and 114 ports. The extraction explicitly selects the GF180D 11K top-metal thickness. This stream produced the same SPEF bytes in a 9K control. The RC model uses lumped resistance and capacitance per net. The timing and tier grader use the released KLT 0.9.2.

```sh
macro=flow/readout/cryo_char_ctrl
uvx --from 'git+https://github.com/2AMLogic/klayout-tools@ab8e93cca745e3bda20a826fd41864eecd5bd9dd' klt extract "$macro.gds" --pdk gf180mcuD --deck gf180mcu --top cryo_char_ctrl --deck-option metal_top=11K --parasitics --def-net-names --def-net-connections "$macro.def" --def-pins "$macro.def" --spef /tmp/cryo_char_ctrl.spef --no-netlist --format json > /tmp/cryo-extract.json
cmp /tmp/cryo_char_ctrl.spef "$macro.spef"
klt sta flow/readout/timing.json --pdk gf180mcuD --format json > /tmp/cryo-timing.json
klt sta flow/readout/timing-stress.json --pdk gf180mcuD --format json > /tmp/cryo-stress.json
```

The [measured-period report](timing.report.json) times the selector at an assumed 100 ns and the eight asynchronous ring inputs at the per-family periods above. Each of the five Liberty corners annotated all 596 design nets, with zero reader warnings and six floating drivers. Worst setup slack is **+0.31881 ns** (slow, 125 °C, 3.0 V). Worst hold is **+0.47046 ns** (fast, −40 °C, 3.6 V). The [stress report](timing-stress.report.json) tightens the 12-track period to 9 ns and holds both foundry families at 12 ns. It records four slow/hot setup violations, worst **−0.18119 ns** from `_247_/Q` to `_256_/D`. Both runs leave 65 endpoints unconstrained, including macro I/O that needs system timing budgets. The evidence supports the digital layout row. Timing closure, DRC signoff and full-die acceptance remain outstanding.
