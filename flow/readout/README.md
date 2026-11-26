# GF180D routed readout controller

The integration input for the die floorplan is [cryo_char_ctrl.gds](cryo_char_ctrl.gds), with port names, coordinates and supply nets in the [routed DEF](cryo_char_ctrl.def). The controller occupies **244.42 × 244.42 µm** including its margin. The selector, eight divide-by-1,024 channels and their reset logic occupy a 49,172.5 µm² core. This build uses the default 1,024-bit `CUT_PATHS=0` mask in the mapped [controller](../../rtl/cryo_char_ctrl.gl.v). Changing a freeze mask requires a new synthesis and route.

The [route record](route.json) binds the 576-cell source netlist, request, DEF and GDS by SHA-256. Detailed routing returned zero markers. The DEF contains 2,840 placed components, including 435 taps, with VDD and VSS special nets. Physical clock-tree synthesis reached 64 selector sinks and twelve sinks on each of eight oscillator roots. The [full P&R report](pnr.report.json) records the nine clocks. The macro passes gate-level signal and supply LVS and structural supply ERC. The full die still needs I/O timing budgets, density closure and the shuttle precheck. [Readout layout tracker](https://github.com/2AMLogic/gf180-cryo-char/issues/17) · [Multi-clock CTS](https://github.com/2AMLogic/klayout-tools/issues/7945) · [Die handoff](https://github.com/2AMLogic/gf180-cryo-char/issues/4)

## Reproduce the layout

Use Python with `klayout-tools==0.9.2`, the KLayout Python package 0.30.14, OpenROAD `26Q3-1510-g6cb3f2b704` on PATH, and `PDK_ROOT` containing gf180mcuD at open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`. The route used the linux/amd64 image `openroad/orfs@sha256:bb7f31697fb8466ab61852fc796376cc16d9df38f762ccb733218b8a5e55824b`. A containerized OpenROAD needs the working directory, resolved temporary directory and PDK accessible at the same absolute paths as on the host. From the repository root:

```sh
python flow/reproduce.py
uv run --no-project --with "klayout-tools @ git+https://github.com/2AMLogic/klayout-tools@4f24005b034d55051ddeded1510ef4b9d185554d" python flow/reproduce.py --reroute
```

The route uses the pinned multi-clock KLT revision above. DRC, LVS, STA, ERC and tier grading use the released 0.9.2. The full replay checks the clock-tree log and physical metrics, then compares the new DEF and the timestamp-free 1 nm GDS with the published bytes. Conversion from the router’s 0.5 nm units compares the merged drawn masks by XOR on every layer and compares cell placements and labels on their original grid. Native DRC used the KLayout 0.30.13 executable. The [curated run](drc-curated.json) found zero markers across 72 checked rules. The [native DRC run](drc-klayout.json) found eight density markers on the macro alone, one each for DCF.1b, PL.8, M1.4 through M5.4, and MT.3. Recheck after die assembly and fill.

```sh
macro=flow/readout/cryo_char_ctrl
klt drc "$macro.gds" --pdk gf180mcuD --deck gf180mcu --top cryo_char_ctrl --engine curated --format json
klt drc "$macro.gds" --pdk gf180mcuD --top cryo_char_ctrl --engine klayout --format json
```

## Divider clocks and supply crossing

The [ngspice bench](../../sim/readout/ring_clock.py) instantiates one gating NAND, 142 inverters and the output buffer from each selected cell family. The primary NIST codes 482, 483, 484 and 487 drive ports 0 through 3. The corresponding replicas drive ports 4 through 7. Codes 483 and 484 share a 9-track electrical model. Routing differences between specimens remain to be extracted.

In the original direct-load control each ring drove twelve 7-track DFF clock inputs. Its nominal 72 fF load combines the largest extracted port wire capacitance (31.529683 fF) with twelve 3.346 fF typical Liberty clock pins. The split-supply control replaces the lumped pin load with twelve transistor-level DFFs, monitors one toggle-connected DFF, and retains the 31.529683 fF wire load.

| GF180 ring family | Typical, 25 °C, 3.3 V at 120 ps step | Fast corner, −40 °C, 3.6 V at 0.625 ps step | Period used in STA |
|---|---:|---:|---:|
| Foundry 7-track | 43.59 MHz | 81.13 MHz | 12.0 ns |
| Foundry 9-track | 45.60 MHz | 80.65 MHz | 12.0 ns |
| OSU 12-track | 63.62 MHz | 101.09 MHz | 9.5 ns |

The [71 simulation cases](ring-clock-measurements.csv) record loads, supplies, process, temperature, timestep, run length and receiver transitions. The [24 timestep controls](ring-step-control.csv) used a 110 ns transient at the fast corner with the 72 fF load. The 5 ps run gave a shortest 12-track period of 9.911 ns. Finer steps yielded 9.897 ns at 2.5 ps and 9.892 ns at 0.625 ps. The timing constraints keep at least 2% period margin against the finest measured case in each family. Internal wire-load cases add 1 or 3 fF per stage. These are schematic models at specified PVT corners. Die routing, device variation and cryogenic operation require separate characterization.

In the direct-load control with VRO at 1.4 V and the receiver at 3.3 V, the typical 7-track ring oscillated at 11.37 MHz while the DFF captured zero of eight complete cycles, at both 120 ps and 40 ps timesteps. At 1.65 V the receiver toggled in every measured window at the tested points. This leaves voltage translation and its qualified supply range open for the die. ngspice 46 and the [model checksums](../../sim/readout/ring_inputs.json) identify the open_pdks build used here. The [eight independent PDK controls](ring-shuttle-controls.csv) repeat the nominal and fast runs and both split-supply cases with the wafer.space files. Its 7- and 9-track families reproduced the open_pdks results at the same 5 ps timestep and both missed all eight measured cycles at 1.4 V. Use `--pdk-source wafer-space --pdk /path/to/shuttle/gf180mcuD` for those cases. The pinned wafer.space bundle uses different transistor-model files and lists foundry 7- and 9-track libraries. The OSU 12-track source needs a separately pinned integration view. [Shuttle PDK](https://github.com/wafer-space/gf180mcu/tree/ac7d8696de96a4d708e768b607ae37f02207a354/gf180mcuD/libs.ref)

```sh
python sim/readout/ring_clock.py 12t ff -40 3.6 --pdk "$PDK_ROOT/gf180mcuD" --step-ns 0.005 --duration-ns 110
python sim/readout/ring_clock.py 7t typical 25 1.4 --pdk "$PDK_ROOT/gf180mcuD" --logic-supply 3.3 --load-ff 31.529683 --duration-ns 950
```

## Capture through the routed clock trees

Each oscillator now drives one seven-track root buffer, two leaf buffers and twelve clocked registers. The [routed receiver bench](../../sim/readout/routed_ring.py) reads the actual cell names, loads and connections from the DEF and uses the lumped SPEF capacitance of each of the four nets. It instantiates the library transistors and clocks a toggle-connected DFF on one leaf. The remaining DFFs and inserted dummy clock loads contribute their actual pin loads. The ring, ring output buffer and its internal wires are still schematic models. Each row of the [capture data](routed-ring-capture.csv) records the monitored clock windows and successful toggles.

At typical 25 °C with the ring at 1.4 V and the controller at 3.3 V, the 7- and 9-track specimens each captured 8/8 cycles and both 12-track specimens captured 17/17. At the fast −40 °C corner with the controller at 3.6 V, every ring still oscillated at 1.4 V, but none of the eight monitored DFFs followed the ring. This crossing needs a level translator or a measured, narrower operating range before the divider can serve as its readout.

The [dual-rail receiver](../../design/ro-crossing/README.md) restores capture at that fast corner with the extracted six-transistor cell. Its two supply-current measurements show the burden on the ring rail for die integration.

| Process and temperature | Ring / controller supply | Captured / complete cycles across eight ports |
|---|---|---:|
| Typical, 25 °C | 1.4 V / 3.3 V | 82/82 |
| Typical, 25 °C | 1.65 V / 3.3 V | 134/134 |
| Fast, −40 °C | 3.6 V / 3.6 V | 52/52 |
| Fast, −40 °C | 1.4 V / 3.6 V | 0/158 |
| Slow, 125 °C | 1.4 V / 3.0 V | 72/72 |

```sh
python sim/readout/routed_ring.py 2 typical 25 1.4 --pdk "$PDK_ROOT/gf180mcuD" --logic-supply 3.3 --duration-ns 950 --step-ns 0.04
python sim/readout/routed_ring.py 2 ff -40 1.4 --pdk "$PDK_ROOT/gf180mcuD" --logic-supply 3.6 --duration-ns 950 --step-ns 0.04
```

## Extract and time the routed macro

Generate the SPEF from the committed GDS with the pinned extractor revision below. Its DEF identifier escaping is required by the OpenROAD reader. The [extraction record](extraction.json) binds its GDS, DEF and output SPEF. It recognized 7,828 devices and 114 ports. The extraction explicitly selects the GF180D 11K top-metal thickness. The RC model uses lumped resistance and capacitance per net. The timing and tier grader use the released KLT 0.9.2.

```sh
macro=flow/readout/cryo_char_ctrl
uvx --from 'git+https://github.com/2AMLogic/klayout-tools@ab8e93cca745e3bda20a826fd41864eecd5bd9dd' klt extract "$macro.gds" --pdk gf180mcuD --deck gf180mcu --top cryo_char_ctrl --deck-option metal_top=11K --parasitics --def-net-names --def-net-connections "$macro.def" --def-pins "$macro.def" --spef /tmp/cryo_char_ctrl.spef --no-netlist --format json > /tmp/cryo-extract.json
cmp /tmp/cryo_char_ctrl.spef "$macro.spef"
python flow/time_readout.py
```

The replay records a SHA-256 of the exact request, DEF and SPEF in each timing report. KLT also records its own DEF provenance. The [measured-period report](timing.report.json) times the selector at an assumed 100 ns and the eight asynchronous ring inputs at the per-family periods above. Each of the five Liberty corners annotated all 620 design nets, with zero reader warnings and thirteen floating drivers. Worst setup slack is **+0.30899 ns** (slow, 125 °C, 3.0 V). Worst hold is **+0.47422 ns** (fast, −40 °C, 3.6 V). The [stress report](timing-stress.report.json) tightens the 12-track period to 9 ns and holds both foundry families at 12 ns. It records four slow/hot setup violations, worst **−0.19101 ns** from `_295_/Q` to `_304_/D`. Both runs leave 65 endpoints unconstrained, including macro I/O that needs system timing budgets. Timing closure, DRC signoff and full-die acceptance remain outstanding.

## Gate-level connectivity

The [LVS report](lvs.report.json) compares the physical GDS to the [as-built Verilog](cryo_char_ctrl.asbuilt.v) regenerated alongside the DEF. The comparison uses the foundry 7-track pin definitions, names extracted nets from the routed layout, and locates the 112 functional terminals using the DEF. The GDS, DEF, reference and [request](lvs.json) are all hash-bound in the report. The request selects GF180D 11K top metal.

Both signal and supply verdicts are `match`. The signal compare has zero errors. Its five informational entries cover unused device classes in this standard-cell black-box comparison, pruning physical-only cells and anchoring public pins. All 2,840 placed instances participate in the VDD/VSS connectivity check, with zero findings. The library exposes these two rail names to the abstract compare. Separate VNW/VPW ties and internal transistor bodies require electrical-rule checking. KLT's reported body device count is zero for this comparison.

Run the following with the PDK and tools from the layout replay. It first compares the published macro, then inserts a real Metal2 bridge between ro_clk[2] and ro_clk[6] in a temporary copy of the GDS. A second control feeds divider 7's bit-zero DFF from ro_clk[6] in a temporary reference. Both controls must produce signal mismatches while the rail verdict remains matched.

```sh
python flow/check_lvs.py --negative-controls
```

## Structural supply check

The [ERC report](erc.report.json) uses the [metal and via stack and tap definitions](erc.json) to check VDD and VSS. Each rail has one connected island. A tap requires a drawn Contact cut (33/0) on diffusion with the appropriate implant. Drawn n-wells are checked for n-type taps connected to VDD. The substrate region is defined as the complement of n-well within the macro boundary and checked for p-type taps connected to VSS. KLT reports the latter as a well assertion. This check covers the digital macro. The findings-only run excludes antenna ratios.

```sh
python flow/check_supply.py --negative-control
```

The control first flattens the stream and verifies that it passes. It then tests two independent opens. Removing 1,094 substrate contact cuts produces one missing VSS tie. Removing 1,641 n-well contact cuts produces 28 missing VDD ties. Both rail islands remain connected in each control.
