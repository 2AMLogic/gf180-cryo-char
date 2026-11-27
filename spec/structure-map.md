# Structure map for GF180MCU-D

Decision 0001 uses the workbook cell as the stable provenance and the first column as the selection code. Codes remain reserved if a structure is dropped or cut at freeze. Each physical GF180 cell has one primary source entry. The placement replicas described below have a separate bank bit. No source layout geometry was taken from GDS.

## Source and reproduction

The source is version 1.1.2 of NIST dataset `mds2-2997`. The workbook describes which device each probe position measures. The companion slides describe module topology, wiring and the two oscillator placement groups. The SHA-256 digests of the original archive and workbook are checked before any cells are read. [NIST dataset](https://data.nist.gov/od/id/mds2-2997)

From the repository root, download the archive outside the checkout and run:

```sh
curl -fL 'https://data.nist.gov/od/ds/mds2-2997/MPW-5%20Test%20Tile.zip' -o /tmp/nist-mpw5.zip
uv run --no-project --with openpyxl==3.1.5 python spec/source_catalog.py /tmp/nist-mpw5.zip --check spec/structure-map.md
```

The 493 primary entries cover 400 array transistors, 16 isolated transistors, 7 MOS capacitor and 21 overlap variants, 7 area diodes, 2 area and 2 perimeter MIM variants, 8 precision resistors, 13 metal meanders, 5 via chains and 12 oscillator libraries. All 287 unique transistor IDs with IDVG/IDVD files in the archive match entries in this map; 113 workbook entries have no such current trace. These are all 56 nthick and 56 pthick array entries and pthin/17_6. Report GF180 measurements for those rows alongside the source geometry with the missing NIST I–V trace identified. The final two sheets contain no structures. A transistor's global row includes the offset in its module header. For example, the first p-channel device is `pthin/11_1`. Split resistor and isolated-FET rows have two independent devices. Conversely, a ring oscillator's two worksheet rows are two pin rows of one circuit. Terminal numerals are source probe positions. In the oscillator rows they are local to R1 and R2.

## Port geometry and exceptions

- W × L and pitches below are in µm. The source columns reproduce the workbook cells, including spelling inconsistencies. The target column gives drawn GF180 dimensions. Standard-voltage FET sweeps add 0.13 µm to channel length to map the shortest 0.15 µm sample to 0.28 µm. The thick-gate n/p sweeps add 0.28/0.13 µm to meet 0.70/0.55 µm minima. The native sweep adds 0.30 µm to W and 1.38 µm to L, taking the smallest device to 0.80 × 1.80. Applying the same offsets to every primary sweep entry retains separate geometry points. For overlap code 442 the source’s 0.42 µm finger would reach only 0.72 µm with the array offset. Draw each finger at the native PCell’s 0.80 µm width minimum and keep the 2.18 µm length. For the other overlap and fixed-area arrays follow the explicit target dimensions below. These are geometry comparisons at common terminal biases. The in-rail 0–3.3 V nominal measurement window samples only the low-bias portion of the source high-voltage structures. Record the actual powered rail. Measurements above that rail, including 5 V and 10.5 V source sweeps, are outside the port. Record drawn and extracted W/L and terminal biases with each result.
- For isolated NMOS codes 401–404 and 409–412, give each separate LVPWELL its own contacted P+ body inside a deep N-well (DNWELL). Route the LVPWELL contact to its selected Kelvin body pair, a separate N-type DNWELL pickup directly to the 3.3 V nominal VDD supply, and the outer P+ guard to VSS. Verify continuity of these three distinct nets by extraction and keep both well junctions reverse biased throughout every accepted sweep. Use the pinned NFET PCell with Bulk Tie, one finger, contact between fingers enabled, 0.52 µm diffusion length and 0.38 µm guard ring width. For codes 401 and 403 the body-tied PCell widens the 0.36 µm source geometry to 0.42 µm; the source width remains in the workbook column. At each mapped W/L the pinned NFET primitive has a contacted body inside LVPWELL and a drawn outer guard. The geometry replay runs the PCell parameter coercion, measures W/L from the drawn gate crossing, and checks the original narrow requests as negative controls. The cell integrator must add the N-type DNWELL pickup and contacted VSS guard. These connections are absent from the bare primitive. A shared substrate body cannot satisfy these eight rows. Isolated PMOS cells use their own contacted N-wells. [Foundry LVPWELL rules](https://gf180mcu-pdk.readthedocs.io/en/latest/physical_verification/design_manual/drm_07_04.html) [Geometry replay](check_isolated_bodies.py) The array port selects each four-terminal DUT independently. An unisolated native or substrate body stays at VSS. Apply a legal source offset to vary body bias and measure the body potential via the substrate witness. An independently driven body or source sweep beyond the common pad-voltage range has no corresponding GF180 measurement. The native structure must never inject a forced current into the chip substrate through a selection switch.
- `MOSCAP2` and `MOSCAPOVL2` use the workbook spelling `npfet_01v8`. The proposed interpretation is the standard p-channel member of the seven-family sequence, supported by the reversed voltage sweep in `cap/moscap2.mdm` compared with `moscap1.mdm`. An independent source review must confirm this before generation. For MOSCAP, area diode and area MIM arrays the workbook supplies the dimensions and the module slides supply the parallel count. In overlap modules “Long” is 30 µm in slides 11–13. Source comb length and electrical gate length are separate dimensions.
- GF180D has five routing metals and the 2 fF/µm² MIM option. Both source MIM placements map to separate specimens of the available M4-to-top stack. For perimeter arrays, scale the original square and pitch fivefold to meet the PCell's 5 µm plate minimum while retaining the original filling fraction. Use a 175 × 175 µm window for each of the 20 repeated arrays (slide 17); center a square grid of complete plates in each window. Code 454 uses 14 × 14 plates per window with 4.4 µm clearance to each edge (3,920 plates total). Code 455 uses 9 × 9 with 2.5 µm edge clearance (1,620 plates total). Extract and report total area and perimeter. The cross-stack dielectric comparison is unavailable. Named metal levels in ResMet are taken literally. The two series with repeated names retain separate selection codes. The serpentine unit has 40 µm straight runs at the GF layer's minimum width/space in a 40 µm transverse window. For the via chain alternate the two named metals and contact each legal turn. Report the realized length, width, via count and Kelvin terminal locations.
- For precision resistors the shorter source dimension of 0.35 µm maps to the target resistor minimum. The four terminal names determine force and sense taps. `PrRES!I3` and `I21` repeat R3T; slides 19–20 show the bottom-force tap at that location. The port uses distinct top/bottom taps. Place the second PRES1-2 and PRES2-2 set as separate specimens with the same W/L, selected by the replica bit. Preserve both records.
- For the retained oscillator families, the 7-track and 9-track foundry libraries represent dense and fast architectures, respectively. The high-voltage reference uses an independent 9-track instance at the common accessible supply. General-purpose OSU 12-track is the mid-speed counterpart. These are family-level comparisons; the SKY threshold implants are technology-specific. Use a 12 × 12 cell array with 142 unit inverters and one inverting enable gate in the feedback path (143 inverting stages), one output buffer, and a divide-by-1024 counter as on slide 25. Document 143 as a GF port choice; the slide specifies the array footprint and divider without numbering active feedback stages. Implement both placement specimens with independent addresses via the replica bit. Record VRO, stage count, divider and measured output frequency with every comparison. [Pinned process option](https://github.com/wafer-space/gf180mcu/blob/ac7d8696de96a4d708e768b607ae37f02207a354/gf180mcuD/.config/nodeinfo.json) · [Selected pad and cell libraries](https://github.com/wafer-space/gf180mcu-project-template/blob/d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c/README.md)

The generator must use the GF180 PDK geometry and pass cell DRC/LVS before integration. Code assignments below describe the proposal and do not certify those tests.

| Select | Workbook cell(s) | NIST module / specimen | Source device | Source geometry or definition | Source terminals | GF180 device, geometry and layout, or reason dropped |
|---|---|---|---|---|---|---|
| 1 | FETModules!B3 | nthin/1_1 | sky130_fd_pr__nfet_01v8 | W=0.36/L=0.15 | 1=B 2=G 3=S 4=D | nfet_03v3, 0.36 × 0.28, nf=1; single device in addressed array |
| 2 | FETModules!B4 | nthin/1_2 | sky130_fd_pr__nfet_01v8 | W=0.39/L=0.15 | 1=B 2=G 4=S 5=D | nfet_03v3, 0.39 × 0.28, nf=1; single device in addressed array |
| 3 | FETModules!B5 | nthin/1_3 | sky130_fd_pr__nfet_01v8 | W=0.42/L=0.15 | 1=B 2=G 5=S 6=D | nfet_03v3, 0.42 × 0.28, nf=1; single device in addressed array |
| 4 | FETModules!B6 | nthin/1_4 | sky130_fd_pr__nfet_01v8 | W=0.42/L=0.18 | 1=B 2=G 6=S 7=D | nfet_03v3, 0.42 × 0.31, nf=1; single device in addressed array |
| 5 | FETModules!B7 | nthin/1_5 | sky130_fd_pr__nfet_01v8 | W=0.42/L=0.25 | 1=B 2=G 7=S 8=D | nfet_03v3, 0.42 × 0.38, nf=1; single device in addressed array |
| 6 | FETModules!B8 | nthin/1_6 | sky130_fd_pr__nfet_01v8 | W=0.42/L=0.5 | 1=B 2=G 8=S 9=D | nfet_03v3, 0.42 × 0.63, nf=1; single device in addressed array |
| 7 | FETModules!B9 | nthin/1_7 | sky130_fd_pr__nfet_01v8 | W=0.42/L=1 | 1=B 2=G 9=S 10=D | nfet_03v3, 0.42 × 1.13, nf=1; single device in addressed array |
| 8 | FETModules!B10 | nthin/1_8 | sky130_fd_pr__nfet_01v8 | W=0.42/L=2 | 1=B 2=G 10=S 11=D | nfet_03v3, 0.42 × 2.13, nf=1; single device in addressed array |
| 9 | FETModules!B11 | nthin/2_1 | sky130_fd_pr__nfet_01v8 | W=0.42/L=4 | 1=B 2=G 3=S 4=D | nfet_03v3, 0.42 × 4.13, nf=1; single device in addressed array |
| 10 | FETModules!B12 | nthin/2_2 | sky130_fd_pr__nfet_01v8 | W=0.42/L=8 | 1=B 2=G 4=S 5=D | nfet_03v3, 0.42 × 8.13, nf=1; single device in addressed array |
| 11 | FETModules!B13 | nthin/2_3 | sky130_fd_pr__nfet_01v8 | W=0.42/L=20 | 1=B 2=G 5=S 6=D | nfet_03v3, 0.42 × 20.13, nf=1; single device in addressed array |
| 12 | FETModules!B14 | nthin/2_4 | sky130_fd_pr__nfet_01v8 | W=0.52/L=0.15 | 1=B 2=G 6=S 7=D | nfet_03v3, 0.52 × 0.28, nf=1; single device in addressed array |
| 13 | FETModules!B15 | nthin/2_5 | sky130_fd_pr__nfet_01v8 | W=0.54/L=0.15 | 1=B 2=G 7=S 8=D | nfet_03v3, 0.54 × 0.28, nf=1; single device in addressed array |
| 14 | FETModules!B16 | nthin/2_6 | sky130_fd_pr__nfet_01v8 | W=0.54/L=0.18 | 1=B 2=G 8=S 9=D | nfet_03v3, 0.54 × 0.31, nf=1; single device in addressed array |
| 15 | FETModules!B17 | nthin/2_7 | sky130_fd_pr__nfet_01v8 | W=0.55/L=0.15 | 1=B 2=G 9=S 10=D | nfet_03v3, 0.55 × 0.28, nf=1; single device in addressed array |
| 16 | FETModules!B18 | nthin/2_8 | sky130_fd_pr__nfet_01v8 | W=0.55/L=0.25 | 1=B 2=G 10=S 11=D | nfet_03v3, 0.55 × 0.38, nf=1; single device in addressed array |
| 17 | FETModules!B19 | nthin/3_1 | sky130_fd_pr__nfet_01v8 | W=0.55/L=0.5 | 1=B 2=G 3=S 4=D | nfet_03v3, 0.55 × 0.63, nf=1; single device in addressed array |
| 18 | FETModules!B20 | nthin/3_2 | sky130_fd_pr__nfet_01v8 | W=0.55/L=1 | 1=B 2=G 4=S 5=D | nfet_03v3, 0.55 × 1.13, nf=1; single device in addressed array |
| 19 | FETModules!B21 | nthin/3_3 | sky130_fd_pr__nfet_01v8 | W=0.55/L=2 | 1=B 2=G 5=S 6=D | nfet_03v3, 0.55 × 2.13, nf=1; single device in addressed array |
| 20 | FETModules!B22 | nthin/3_4 | sky130_fd_pr__nfet_01v8 | W=0.55/L=4 | 1=B 2=G 6=S 7=D | nfet_03v3, 0.55 × 4.13, nf=1; single device in addressed array |
| 21 | FETModules!B23 | nthin/3_5 | sky130_fd_pr__nfet_01v8 | W=0.55/L=8 | 1=B 2=G 7=S 8=D | nfet_03v3, 0.55 × 8.13, nf=1; single device in addressed array |
| 22 | FETModules!B24 | nthin/3_6 | sky130_fd_pr__nfet_01v8 | W=0.6/L=0.15 | 1=B 2=G 8=S 9=D | nfet_03v3, 0.6 × 0.28, nf=1; single device in addressed array |
| 23 | FETModules!B25 | nthin/3_7 | sky130_fd_pr__nfet_01v8 | W=0.61/L=0.15 | 1=B 2=G 9=S 10=D | nfet_03v3, 0.61 × 0.28, nf=1; single device in addressed array |
| 24 | FETModules!B26 | nthin/3_8 | sky130_fd_pr__nfet_01v8 | W=0.61/L=0.25 | 1=B 2=G 10=S 11=D | nfet_03v3, 0.61 × 0.38, nf=1; single device in addressed array |
| 25 | FETModules!B27 | nthin/4_1 | sky130_fd_pr__nfet_01v8 | W=0.64/L=0.15 | 1=B 2=G 3=S 4=D | nfet_03v3, 0.64 × 0.28, nf=1; single device in addressed array |
| 26 | FETModules!B28 | nthin/4_2 | sky130_fd_pr__nfet_01v8 | W=0.65/L=0.15 | 1=B 2=G 4=S 5=D | nfet_03v3, 0.65 × 0.28, nf=1; single device in addressed array |
| 27 | FETModules!B29 | nthin/4_3 | sky130_fd_pr__nfet_01v8 | W=0.65/L=0.18 | 1=B 2=G 5=S 6=D | nfet_03v3, 0.65 × 0.31, nf=1; single device in addressed array |
| 28 | FETModules!B30 | nthin/4_4 | sky130_fd_pr__nfet_01v8 | W=0.65/L=0.25 | 1=B 2=G 6=S 7=D | nfet_03v3, 0.65 × 0.38, nf=1; single device in addressed array |
| 29 | FETModules!B31 | nthin/4_5 | sky130_fd_pr__nfet_01v8 | W=0.65/L=0.5 | 1=B 2=G 7=S 8=D | nfet_03v3, 0.65 × 0.63, nf=1; single device in addressed array |
| 30 | FETModules!B32 | nthin/4_6 | sky130_fd_pr__nfet_01v8 | W=0.65/L=1 | 1=B 2=G 8=S 9=D | nfet_03v3, 0.65 × 1.13, nf=1; single device in addressed array |
| 31 | FETModules!B33 | nthin/4_7 | sky130_fd_pr__nfet_01v8 | W=0.65/L=2 | 1=B 2=G 9=S 10=D | nfet_03v3, 0.65 × 2.13, nf=1; single device in addressed array |
| 32 | FETModules!B34 | nthin/4_8 | sky130_fd_pr__nfet_01v8 | W=0.65/L=4 | 1=B 2=G 10=S 11=D | nfet_03v3, 0.65 × 4.13, nf=1; single device in addressed array |
| 33 | FETModules!B35 | nthin/5_1 | sky130_fd_pr__nfet_01v8 | W=0.65/L=8 | 1=B 2=G 3=S 4=D | nfet_03v3, 0.65 × 8.13, nf=1; single device in addressed array |
| 34 | FETModules!B36 | nthin/5_2 | sky130_fd_pr__nfet_01v8 | W=0.65/L=20 | 1=B 2=G 4=S 5=D | nfet_03v3, 0.65 × 20.13, nf=1; single device in addressed array |
| 35 | FETModules!B37 | nthin/5_3 | sky130_fd_pr__nfet_01v8 | W=0.74/L=0.15 | 1=B 2=G 5=S 6=D | nfet_03v3, 0.74 × 0.28, nf=1; single device in addressed array |
| 36 | FETModules!B38 | nthin/5_4 | sky130_fd_pr__nfet_01v8 | W=0.74/L=0.25 | 1=B 2=G 6=S 7=D | nfet_03v3, 0.74 × 0.38, nf=1; single device in addressed array |
| 37 | FETModules!B39 | nthin/5_5 | sky130_fd_pr__nfet_01v8 | W=0.74/L=8 | 1=B 2=G 7=S 8=D | nfet_03v3, 0.74 × 8.13, nf=1; single device in addressed array |
| 38 | FETModules!B40 | nthin/5_6 | sky130_fd_pr__nfet_01v8 | W=0.84/L=0.15 | 1=B 2=G 8=S 9=D | nfet_03v3, 0.84 × 0.28, nf=1; single device in addressed array |
| 39 | FETModules!B41 | nthin/5_7 | sky130_fd_pr__nfet_01v8 | W=1/L=0.15 | 1=B 2=G 9=S 10=D | nfet_03v3, 1 × 0.28, nf=1; single device in addressed array |
| 40 | FETModules!B42 | nthin/5_8 | sky130_fd_pr__nfet_01v8 | W=1/L=0.18 | 1=B 2=G 10=S 11=D | nfet_03v3, 1 × 0.31, nf=1; single device in addressed array |
| 41 | FETModules!B43 | nthin/6_1 | sky130_fd_pr__nfet_01v8 | W=1/L=0.25 | 1=B 2=G 3=S 4=D | nfet_03v3, 1 × 0.38, nf=1; single device in addressed array |
| 42 | FETModules!B44 | nthin/6_2 | sky130_fd_pr__nfet_01v8 | W=1/L=1 | 1=B 2=G 4=S 5=D | nfet_03v3, 1 × 1.13, nf=1; single device in addressed array |
| 43 | FETModules!B45 | nthin/6_3 | sky130_fd_pr__nfet_01v8 | W=1/L=2 | 1=B 2=G 5=S 6=D | nfet_03v3, 1 × 2.13, nf=1; single device in addressed array |
| 44 | FETModules!B46 | nthin/6_4 | sky130_fd_pr__nfet_01v8 | W=1/L=4 | 1=B 2=G 6=S 7=D | nfet_03v3, 1 × 4.13, nf=1; single device in addressed array |
| 45 | FETModules!B47 | nthin/6_5 | sky130_fd_pr__nfet_01v8 | W=1/L=8 | 1=B 2=G 7=S 8=D | nfet_03v3, 1 × 8.13, nf=1; single device in addressed array |
| 46 | FETModules!B48 | nthin/6_6 | sky130_fd_pr__nfet_01v8 | W=1.26/L=0.15 | 1=B 2=G 8=S 9=D | nfet_03v3, 1.26 × 0.28, nf=1; single device in addressed array |
| 47 | FETModules!B49 | nthin/6_7 | sky130_fd_pr__nfet_01v8 | W=1.68/L=0.15 | 1=B 2=G 9=S 10=D | nfet_03v3, 1.68 × 0.28, nf=1; single device in addressed array |
| 48 | FETModules!B50 | nthin/6_8 | sky130_fd_pr__nfet_01v8 | W=1.68/L=0.18 | 1=B 2=G 10=S 11=D | nfet_03v3, 1.68 × 0.31, nf=1; single device in addressed array |
| 49 | FETModules!B51 | nthin/7_1 | sky130_fd_pr__nfet_01v8 | W=1.68/L=0.25 | 1=B 2=G 3=S 4=D | nfet_03v3, 1.68 × 0.38, nf=1; single device in addressed array |
| 50 | FETModules!B52 | nthin/7_2 | sky130_fd_pr__nfet_01v8 | W=1.68/L=1 | 1=B 2=G 4=S 5=D | nfet_03v3, 1.68 × 1.13, nf=1; single device in addressed array |
| 51 | FETModules!B53 | nthin/7_3 | sky130_fd_pr__nfet_01v8 | W=1.68/L=2 | 1=B 2=G 5=S 6=D | nfet_03v3, 1.68 × 2.13, nf=1; single device in addressed array |
| 52 | FETModules!B54 | nthin/7_4 | sky130_fd_pr__nfet_01v8 | W=1.68/L=4 | 1=B 2=G 6=S 7=D | nfet_03v3, 1.68 × 4.13, nf=1; single device in addressed array |
| 53 | FETModules!B55 | nthin/7_5 | sky130_fd_pr__nfet_01v8 | W=1.68/L=8 | 1=B 2=G 7=S 8=D | nfet_03v3, 1.68 × 8.13, nf=1; single device in addressed array |
| 54 | FETModules!B56 | nthin/7_6 | sky130_fd_pr__nfet_01v8 | W=1.68/L=20 | 1=B 2=G 8=S 9=D | nfet_03v3, 1.68 × 20.13, nf=1; single device in addressed array |
| 55 | FETModules!B57 | nthin/7_7 | sky130_fd_pr__nfet_01v8 | W=2/L=0.15 | 1=B 2=G 9=S 10=D | nfet_03v3, 2 × 0.28, nf=1; single device in addressed array |
| 56 | FETModules!B58 | nthin/7_8 | sky130_fd_pr__nfet_01v8 | W=3/L=0.15 | 1=B 2=G 10=S 11=D | nfet_03v3, 3 × 0.28, nf=1; single device in addressed array |
| 57 | FETModules!B59 | nthin/8_1 | sky130_fd_pr__nfet_01v8 | W=3/L=0.18 | 1=B 2=G 3=S 4=D | nfet_03v3, 3 × 0.31, nf=1; single device in addressed array |
| 58 | FETModules!B60 | nthin/8_2 | sky130_fd_pr__nfet_01v8 | W=3/L=0.25 | 1=B 2=G 4=S 5=D | nfet_03v3, 3 × 0.38, nf=1; single device in addressed array |
| 59 | FETModules!B61 | nthin/8_3 | sky130_fd_pr__nfet_01v8 | W=3/L=0.5 | 1=B 2=G 5=S 6=D | nfet_03v3, 3 × 0.63, nf=1; single device in addressed array |
| 60 | FETModules!B62 | nthin/8_4 | sky130_fd_pr__nfet_01v8 | W=3/L=1 | 1=B 2=G 6=S 7=D | nfet_03v3, 3 × 1.13, nf=1; single device in addressed array |
| 61 | FETModules!B63 | nthin/8_5 | sky130_fd_pr__nfet_01v8 | W=3/L=2 | 1=B 2=G 7=S 8=D | nfet_03v3, 3 × 2.13, nf=1; single device in addressed array |
| 62 | FETModules!B64 | nthin/8_6 | sky130_fd_pr__nfet_01v8 | W=3/L=4 | 1=B 2=G 8=S 9=D | nfet_03v3, 3 × 4.13, nf=1; single device in addressed array |
| 63 | FETModules!B65 | nthin/8_7 | sky130_fd_pr__nfet_01v8 | W=3/L=8 | 1=B 2=G 9=S 10=D | nfet_03v3, 3 × 8.13, nf=1; single device in addressed array |
| 64 | FETModules!B66 | nthin/8_8 | sky130_fd_pr__nfet_01v8 | W=5/L=0.15 | 1=B 2=G 10=S 11=D | nfet_03v3, 5 × 0.28, nf=1; single device in addressed array |
| 65 | FETModules!B67 | nthin/9_1 | sky130_fd_pr__nfet_01v8 | W=5/L=0.18 | 1=B 2=G 3=S 4=D | nfet_03v3, 5 × 0.31, nf=1; single device in addressed array |
| 66 | FETModules!B68 | nthin/9_2 | sky130_fd_pr__nfet_01v8 | W=5/L=0.25 | 1=B 2=G 4=S 5=D | nfet_03v3, 5 × 0.38, nf=1; single device in addressed array |
| 67 | FETModules!B69 | nthin/9_3 | sky130_fd_pr__nfet_01v8 | W=5/L=0.5 | 1=B 2=G 5=S 6=D | nfet_03v3, 5 × 0.63, nf=1; single device in addressed array |
| 68 | FETModules!B70 | nthin/9_4 | sky130_fd_pr__nfet_01v8 | W=5/L=1 | 1=B 2=G 6=S 7=D | nfet_03v3, 5 × 1.13, nf=1; single device in addressed array |
| 69 | FETModules!B71 | nthin/9_5 | sky130_fd_pr__nfet_01v8 | W=5/L=2 | 1=B 2=G 7=S 8=D | nfet_03v3, 5 × 2.13, nf=1; single device in addressed array |
| 70 | FETModules!B72 | nthin/9_6 | sky130_fd_pr__nfet_01v8 | W=5/L=4 | 1=B 2=G 8=S 9=D | nfet_03v3, 5 × 4.13, nf=1; single device in addressed array |
| 71 | FETModules!B73 | nthin/9_7 | sky130_fd_pr__nfet_01v8 | W=5/L=8 | 1=B 2=G 9=S 10=D | nfet_03v3, 5 × 8.13, nf=1; single device in addressed array |
| 72 | FETModules!B74 | nthin/9_8 | sky130_fd_pr__nfet_01v8 | W=7/L=0.15 | 1=B 2=G 10=S 11=D | nfet_03v3, 7 × 0.28, nf=1; single device in addressed array |
| 73 | FETModules!B75 | nthin/10_1 | sky130_fd_pr__nfet_01v8 | W=7/L=0.18 | 1=B 2=G 3=S 4=D | nfet_03v3, 7 × 0.31, nf=1; single device in addressed array |
| 74 | FETModules!B76 | nthin/10_2 | sky130_fd_pr__nfet_01v8 | W=7/L=0.25 | 1=B 2=G 4=S 5=D | nfet_03v3, 7 × 0.38, nf=1; single device in addressed array |
| 75 | FETModules!B77 | nthin/10_3 | sky130_fd_pr__nfet_01v8 | W=7/L=0.5 | 1=B 2=G 5=S 6=D | nfet_03v3, 7 × 0.63, nf=1; single device in addressed array |
| 76 | FETModules!B78 | nthin/10_4 | sky130_fd_pr__nfet_01v8 | W=7/L=1 | 1=B 2=G 6=S 7=D | nfet_03v3, 7 × 1.13, nf=1; single device in addressed array |
| 77 | FETModules!B79 | nthin/10_5 | sky130_fd_pr__nfet_01v8 | W=7/L=2 | 1=B 2=G 7=S 8=D | nfet_03v3, 7 × 2.13, nf=1; single device in addressed array |
| 78 | FETModules!B80 | nthin/10_6 | sky130_fd_pr__nfet_01v8 | W=7/L=4 | 1=B 2=G 8=S 9=D | nfet_03v3, 7 × 4.13, nf=1; single device in addressed array |
| 79 | FETModules!B81 | nthin/10_7 | sky130_fd_pr__nfet_01v8 | W=7/L=8 | 1=B 2=G 9=S 10=D | nfet_03v3, 7 × 8.13, nf=1; single device in addressed array |
| 80 | FETModules!B82 | nthin/10_8 | sky130_fd_pr__nfet_01v8 | W=7/L=20 | 1=B 2=G 10=S 11=D | nfet_03v3, 7 × 20.13, nf=1; single device in addressed array |
| 81 | FETModules!B85 | pthin/11_1 | sky130_fd_pr__pfet_01v8 | W=0.42/L=0.15 | 1=B 2=G 3=S 4=D | pfet_03v3, 0.42 × 0.28, nf=1; single device in addressed array |
| 82 | FETModules!B86 | pthin/11_2 | sky130_fd_pr__pfet_01v8 | W=0.42/L=0.18 | 1=B 2=G 4=S 5=D | pfet_03v3, 0.42 × 0.31, nf=1; single device in addressed array |
| 83 | FETModules!B87 | pthin/11_3 | sky130_fd_pr__pfet_01v8 | W=0.42/L=0.25 | 1=B 2=G 5=S 6=D | pfet_03v3, 0.42 × 0.38, nf=1; single device in addressed array |
| 84 | FETModules!B88 | pthin/11_4 | sky130_fd_pr__pfet_01v8 | W=0.42/L=0.5 | 1=B 2=G 6=S 7=D | pfet_03v3, 0.42 × 0.63, nf=1; single device in addressed array |
| 85 | FETModules!B89 | pthin/11_5 | sky130_fd_pr__pfet_01v8 | W=0.42/L=1 | 1=B 2=G 7=S 8=D | pfet_03v3, 0.42 × 1.13, nf=1; single device in addressed array |
| 86 | FETModules!B90 | pthin/11_6 | sky130_fd_pr__pfet_01v8 | W=0.42/L=2 | 1=B 2=G 8=S 9=D | pfet_03v3, 0.42 × 2.13, nf=1; single device in addressed array |
| 87 | FETModules!B91 | pthin/11_7 | sky130_fd_pr__pfet_01v8 | W=0.42/L=4 | 1=B 2=G 9=S 10=D | pfet_03v3, 0.42 × 4.13, nf=1; single device in addressed array |
| 88 | FETModules!B92 | pthin/11_8 | sky130_fd_pr__pfet_01v8 | W=0.42/L=8 | 1=B 2=G 10=S 11=D | pfet_03v3, 0.42 × 8.13, nf=1; single device in addressed array |
| 89 | FETModules!B93 | pthin/12_1 | sky130_fd_pr__pfet_01v8 | W=0.42/L=20 | 1=B 2=G 3=S 4=D | pfet_03v3, 0.42 × 20.13, nf=1; single device in addressed array |
| 90 | FETModules!B94 | pthin/12_2 | sky130_fd_pr__pfet_01v8 | W=0.55/L=0.15 | 1=B 2=G 4=S 5=D | pfet_03v3, 0.55 × 0.28, nf=1; single device in addressed array |
| 91 | FETModules!B95 | pthin/12_3 | sky130_fd_pr__pfet_01v8 | W=0.55/L=0.25 | 1=B 2=G 5=S 6=D | pfet_03v3, 0.55 × 0.38, nf=1; single device in addressed array |
| 92 | FETModules!B96 | pthin/12_4 | sky130_fd_pr__pfet_01v8 | W=0.55/L=0.5 | 1=B 2=G 6=S 7=D | pfet_03v3, 0.55 × 0.63, nf=1; single device in addressed array |
| 93 | FETModules!B97 | pthin/12_5 | sky130_fd_pr__pfet_01v8 | W=0.55/L=1 | 1=B 2=G 7=S 8=D | pfet_03v3, 0.55 × 1.13, nf=1; single device in addressed array |
| 94 | FETModules!B98 | pthin/12_6 | sky130_fd_pr__pfet_01v8 | W=0.55/L=2 | 1=B 2=G 8=S 9=D | pfet_03v3, 0.55 × 2.13, nf=1; single device in addressed array |
| 95 | FETModules!B99 | pthin/12_7 | sky130_fd_pr__pfet_01v8 | W=0.55/L=4 | 1=B 2=G 9=S 10=D | pfet_03v3, 0.55 × 4.13, nf=1; single device in addressed array |
| 96 | FETModules!B100 | pthin/12_8 | sky130_fd_pr__pfet_01v8 | W=0.55/L=8 | 1=B 2=G 10=S 11=D | pfet_03v3, 0.55 × 8.13, nf=1; single device in addressed array |
| 97 | FETModules!B101 | pthin/13_1 | sky130_fd_pr__pfet_01v8 | W=0.55/L=20 | 1=B 2=G 3=S 4=D | pfet_03v3, 0.55 × 20.13, nf=1; single device in addressed array |
| 98 | FETModules!B102 | pthin/13_2 | sky130_fd_pr__pfet_01v8 | W=0.64/L=0.15 | 1=B 2=G 4=S 5=D | pfet_03v3, 0.64 × 0.28, nf=1; single device in addressed array |
| 99 | FETModules!B103 | pthin/13_3 | sky130_fd_pr__pfet_01v8 | W=0.64/L=0.18 | 1=B 2=G 5=S 6=D | pfet_03v3, 0.64 × 0.31, nf=1; single device in addressed array |
| 100 | FETModules!B104 | pthin/13_4 | sky130_fd_pr__pfet_01v8 | W=0.64/L=0.25 | 1=B 2=G 6=S 7=D | pfet_03v3, 0.64 × 0.38, nf=1; single device in addressed array |
| 101 | FETModules!B105 | pthin/13_5 | sky130_fd_pr__pfet_01v8 | W=0.64/L=0.5 | 1=B 2=G 7=S 8=D | pfet_03v3, 0.64 × 0.63, nf=1; single device in addressed array |
| 102 | FETModules!B106 | pthin/13_6 | sky130_fd_pr__pfet_01v8 | W=0.64/L=1 | 1=B 2=G 8=S 9=D | pfet_03v3, 0.64 × 1.13, nf=1; single device in addressed array |
| 103 | FETModules!B107 | pthin/13_7 | sky130_fd_pr__pfet_01v8 | W=0.64/L=4 | 1=B 2=G 9=S 10=D | pfet_03v3, 0.64 × 4.13, nf=1; single device in addressed array |
| 104 | FETModules!B108 | pthin/13_8 | sky130_fd_pr__pfet_01v8 | W=0.64/L=20 | 1=B 2=G 10=S 11=D | pfet_03v3, 0.64 × 20.13, nf=1; single device in addressed array |
| 105 | FETModules!B109 | pthin/14_1 | sky130_fd_pr__pfet_01v8 | W=0.84/L=0.15 | 1=B 2=G 3=S 4=D | pfet_03v3, 0.84 × 0.28, nf=1; single device in addressed array |
| 106 | FETModules!B110 | pthin/14_2 | sky130_fd_pr__pfet_01v8 | W=1/L=0.15 | 1=B 2=G 4=S 5=D | pfet_03v3, 1 × 0.28, nf=1; single device in addressed array |
| 107 | FETModules!B111 | pthin/14_3 | sky130_fd_pr__pfet_01v8 | W=1/L=0.18 | 1=B 2=G 5=S 6=D | pfet_03v3, 1 × 0.31, nf=1; single device in addressed array |
| 108 | FETModules!B112 | pthin/14_4 | sky130_fd_pr__pfet_01v8 | W=1/L=0.25 | 1=B 2=G 6=S 7=D | pfet_03v3, 1 × 0.38, nf=1; single device in addressed array |
| 109 | FETModules!B113 | pthin/14_5 | sky130_fd_pr__pfet_01v8 | W=1/L=0.5 | 1=B 2=G 7=S 8=D | pfet_03v3, 1 × 0.63, nf=1; single device in addressed array |
| 110 | FETModules!B114 | pthin/14_6 | sky130_fd_pr__pfet_01v8 | W=1/L=1 | 1=B 2=G 8=S 9=D | pfet_03v3, 1 × 1.13, nf=1; single device in addressed array |
| 111 | FETModules!B115 | pthin/14_7 | sky130_fd_pr__pfet_01v8 | W=1/L=2 | 1=B 2=G 9=S 10=D | pfet_03v3, 1 × 2.13, nf=1; single device in addressed array |
| 112 | FETModules!B116 | pthin/14_8 | sky130_fd_pr__pfet_01v8 | W=1/L=4 | 1=B 2=G 10=S 11=D | pfet_03v3, 1 × 4.13, nf=1; single device in addressed array |
| 113 | FETModules!B117 | pthin/15_1 | sky130_fd_pr__pfet_01v8 | W=1/L=8 | 1=B 2=G 3=S 4=D | pfet_03v3, 1 × 8.13, nf=1; single device in addressed array |
| 114 | FETModules!B118 | pthin/15_2 | sky130_fd_pr__pfet_01v8 | W=1.26/L=0.15 | 1=B 2=G 4=S 5=D | pfet_03v3, 1.26 × 0.28, nf=1; single device in addressed array |
| 115 | FETModules!B119 | pthin/15_3 | sky130_fd_pr__pfet_01v8 | W=1.26/L=1 | 1=B 2=G 5=S 6=D | pfet_03v3, 1.26 × 1.13, nf=1; single device in addressed array |
| 116 | FETModules!B120 | pthin/15_4 | sky130_fd_pr__pfet_01v8 | W=1.26/L=20 | 1=B 2=G 6=S 7=D | pfet_03v3, 1.26 × 20.13, nf=1; single device in addressed array |
| 117 | FETModules!B121 | pthin/15_5 | sky130_fd_pr__pfet_01v8 | W=1.65/L=0.15 | 1=B 2=G 7=S 8=D | pfet_03v3, 1.65 × 0.28, nf=1; single device in addressed array |
| 118 | FETModules!B122 | pthin/15_6 | sky130_fd_pr__pfet_01v8 | W=1.68/L=0.15 | 1=B 2=G 8=S 9=D | pfet_03v3, 1.68 × 0.28, nf=1; single device in addressed array |
| 119 | FETModules!B123 | pthin/15_7 | sky130_fd_pr__pfet_01v8 | W=1.68/L=0.18 | 1=B 2=G 9=S 10=D | pfet_03v3, 1.68 × 0.31, nf=1; single device in addressed array |
| 120 | FETModules!B124 | pthin/15_8 | sky130_fd_pr__pfet_01v8 | W=1.68/L=0.25 | 1=B 2=G 10=S 11=D | pfet_03v3, 1.68 × 0.38, nf=1; single device in addressed array |
| 121 | FETModules!B125 | pthin/16_1 | sky130_fd_pr__pfet_01v8 | W=1.68/L=0.5 | 1=B 2=G 3=S 4=D | pfet_03v3, 1.68 × 0.63, nf=1; single device in addressed array |
| 122 | FETModules!B126 | pthin/16_2 | sky130_fd_pr__pfet_01v8 | W=1.68/L=1 | 1=B 2=G 4=S 5=D | pfet_03v3, 1.68 × 1.13, nf=1; single device in addressed array |
| 123 | FETModules!B127 | pthin/16_3 | sky130_fd_pr__pfet_01v8 | W=1.68/L=4 | 1=B 2=G 5=S 6=D | pfet_03v3, 1.68 × 4.13, nf=1; single device in addressed array |
| 124 | FETModules!B128 | pthin/16_4 | sky130_fd_pr__pfet_01v8 | W=1.68/L=8 | 1=B 2=G 6=S 7=D | pfet_03v3, 1.68 × 8.13, nf=1; single device in addressed array |
| 125 | FETModules!B129 | pthin/16_5 | sky130_fd_pr__pfet_01v8 | W=1.68/L=20 | 1=B 2=G 7=S 8=D | pfet_03v3, 1.68 × 20.13, nf=1; single device in addressed array |
| 126 | FETModules!B130 | pthin/16_6 | sky130_fd_pr__pfet_01v8 | W=2/L=0.15 | 1=B 2=G 8=S 9=D | pfet_03v3, 2 × 0.28, nf=1; single device in addressed array |
| 127 | FETModules!B131 | pthin/16_7 | sky130_fd_pr__pfet_01v8 | W=3/L=0.15 | 1=B 2=G 9=S 10=D | pfet_03v3, 3 × 0.28, nf=1; single device in addressed array |
| 128 | FETModules!B132 | pthin/16_8 | sky130_fd_pr__pfet_01v8 | W=3/L=0.18 | 1=B 2=G 10=S 11=D | pfet_03v3, 3 × 0.31, nf=1; single device in addressed array |
| 129 | FETModules!B133 | pthin/17_1 | sky130_fd_pr__pfet_01v8 | W=3/L=0.25 | 1=B 2=G 3=S 4=D | pfet_03v3, 3 × 0.38, nf=1; single device in addressed array |
| 130 | FETModules!B134 | pthin/17_2 | sky130_fd_pr__pfet_01v8 | W=3/L=0.5 | 1=B 2=G 4=S 5=D | pfet_03v3, 3 × 0.63, nf=1; single device in addressed array |
| 131 | FETModules!B135 | pthin/17_3 | sky130_fd_pr__pfet_01v8 | W=3/L=1 | 1=B 2=G 5=S 6=D | pfet_03v3, 3 × 1.13, nf=1; single device in addressed array |
| 132 | FETModules!B136 | pthin/17_4 | sky130_fd_pr__pfet_01v8 | W=3/L=2 | 1=B 2=G 6=S 7=D | pfet_03v3, 3 × 2.13, nf=1; single device in addressed array |
| 133 | FETModules!B137 | pthin/17_5 | sky130_fd_pr__pfet_01v8 | W=3/L=4 | 1=B 2=G 7=S 8=D | pfet_03v3, 3 × 4.13, nf=1; single device in addressed array |
| 134 | FETModules!B138 | pthin/17_6 | sky130_fd_pr__pfet_01v8 | W=3/L=8 | 1=B 2=G 8=S 9=D | pfet_03v3, 3 × 8.13, nf=1; single device in addressed array |
| 135 | FETModules!B139 | pthin/17_7 | sky130_fd_pr__pfet_01v8 | W=3/L=20 | 1=B 2=G 9=S 10=D | pfet_03v3, 3 × 20.13, nf=1; single device in addressed array |
| 136 | FETModules!B140 | pthin/17_8 | sky130_fd_pr__pfet_01v8 | W=5/L=0.15 | 1=B 2=G 10=S 11=D | pfet_03v3, 5 × 0.28, nf=1; single device in addressed array |
| 137 | FETModules!B141 | pthin/18_1 | sky130_fd_pr__pfet_01v8 | W=5/L=0.18 | 1=B 2=G 3=S 4=D | pfet_03v3, 5 × 0.31, nf=1; single device in addressed array |
| 138 | FETModules!B142 | pthin/18_2 | sky130_fd_pr__pfet_01v8 | W=5/L=0.25 | 1=B 2=G 4=S 5=D | pfet_03v3, 5 × 0.38, nf=1; single device in addressed array |
| 139 | FETModules!B143 | pthin/18_3 | sky130_fd_pr__pfet_01v8 | W=5/L=0.5 | 1=B 2=G 5=S 6=D | pfet_03v3, 5 × 0.63, nf=1; single device in addressed array |
| 140 | FETModules!B144 | pthin/18_4 | sky130_fd_pr__pfet_01v8 | W=5/L=1 | 1=B 2=G 6=S 7=D | pfet_03v3, 5 × 1.13, nf=1; single device in addressed array |
| 141 | FETModules!B145 | pthin/18_5 | sky130_fd_pr__pfet_01v8 | W=5/L=2 | 1=B 2=G 7=S 8=D | pfet_03v3, 5 × 2.13, nf=1; single device in addressed array |
| 142 | FETModules!B146 | pthin/18_6 | sky130_fd_pr__pfet_01v8 | W=5/L=4 | 1=B 2=G 8=S 9=D | pfet_03v3, 5 × 4.13, nf=1; single device in addressed array |
| 143 | FETModules!B147 | pthin/18_7 | sky130_fd_pr__pfet_01v8 | W=5/L=8 | 1=B 2=G 9=S 10=D | pfet_03v3, 5 × 8.13, nf=1; single device in addressed array |
| 144 | FETModules!B148 | pthin/18_8 | sky130_fd_pr__pfet_01v8 | W=7/L=0.15 | 1=B 2=G 10=S 11=D | pfet_03v3, 7 × 0.28, nf=1; single device in addressed array |
| 145 | FETModules!B149 | pthin/19_1 | sky130_fd_pr__pfet_01v8 | W=7/L=0.18 | 1=B 2=G 3=S 4=D | pfet_03v3, 7 × 0.31, nf=1; single device in addressed array |
| 146 | FETModules!B150 | pthin/19_2 | sky130_fd_pr__pfet_01v8 | W=7/L=0.25 | 1=B 2=G 4=S 5=D | pfet_03v3, 7 × 0.38, nf=1; single device in addressed array |
| 147 | FETModules!B151 | pthin/19_3 | sky130_fd_pr__pfet_01v8 | W=7/L=0.5 | 1=B 2=G 5=S 6=D | pfet_03v3, 7 × 0.63, nf=1; single device in addressed array |
| 148 | FETModules!B152 | pthin/19_4 | sky130_fd_pr__pfet_01v8 | W=7/L=1 | 1=B 2=G 6=S 7=D | pfet_03v3, 7 × 1.13, nf=1; single device in addressed array |
| 149 | FETModules!B153 | pthin/19_5 | sky130_fd_pr__pfet_01v8 | W=7/L=2 | 1=B 2=G 7=S 8=D | pfet_03v3, 7 × 2.13, nf=1; single device in addressed array |
| 150 | FETModules!B154 | pthin/19_6 | sky130_fd_pr__pfet_01v8 | W=7/L=4 | 1=B 2=G 8=S 9=D | pfet_03v3, 7 × 4.13, nf=1; single device in addressed array |
| 151 | FETModules!B155 | pthin/19_7 | sky130_fd_pr__pfet_01v8 | W=7/L=8 | 1=B 2=G 9=S 10=D | pfet_03v3, 7 × 8.13, nf=1; single device in addressed array |
| 152 | FETModules!B156 | pthin/19_8 | sky130_fd_pr__pfet_01v8 | W=7/L=20 | 1=B 2=G 10=S 11=D | pfet_03v3, 7 × 20.13, nf=1; single device in addressed array |
| 153 | FETModules!B159 | nthin_lvt/20_1 | sky130_fd_pr__nfet_01v8_lvt | W=0.42/L=0.15 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 154 | FETModules!B160 | nthin_lvt/20_2 | sky130_fd_pr__nfet_01v8_lvt | W=0.42/L=0.18 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 155 | FETModules!B161 | nthin_lvt/20_3 | sky130_fd_pr__nfet_01v8_lvt | W=0.42/L=0.25 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 156 | FETModules!B162 | nthin_lvt/20_4 | sky130_fd_pr__nfet_01v8_lvt | W=0.42/L=1 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 157 | FETModules!B163 | nthin_lvt/20_5 | sky130_fd_pr__nfet_01v8_lvt | W=0.42/L=8 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 158 | FETModules!B164 | nthin_lvt/20_6 | sky130_fd_pr__nfet_01v8_lvt | W=0.55/L=0.15 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 159 | FETModules!B165 | nthin_lvt/20_7 | sky130_fd_pr__nfet_01v8_lvt | W=0.55/L=0.25 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 160 | FETModules!B166 | nthin_lvt/20_8 | sky130_fd_pr__nfet_01v8_lvt | W=0.55/L=1 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 161 | FETModules!B167 | nthin_lvt/21_1 | sky130_fd_pr__nfet_01v8_lvt | W=0.55/L=8 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 162 | FETModules!B168 | nthin_lvt/21_2 | sky130_fd_pr__nfet_01v8_lvt | W=0.64/L=0.15 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 163 | FETModules!B169 | nthin_lvt/21_3 | sky130_fd_pr__nfet_01v8_lvt | W=0.64/L=0.18 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 164 | FETModules!B170 | nthin_lvt/21_4 | sky130_fd_pr__nfet_01v8_lvt | W=0.64/L=0.25 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 165 | FETModules!B171 | nthin_lvt/21_5 | sky130_fd_pr__nfet_01v8_lvt | W=0.64/L=0.5 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 166 | FETModules!B172 | nthin_lvt/21_6 | sky130_fd_pr__nfet_01v8_lvt | W=0.64/L=1 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 167 | FETModules!B173 | nthin_lvt/21_7 | sky130_fd_pr__nfet_01v8_lvt | W=0.64/L=2 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 168 | FETModules!B174 | nthin_lvt/21_8 | sky130_fd_pr__nfet_01v8_lvt | W=0.64/L=8 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 169 | FETModules!B175 | nthin_lvt/22_1 | sky130_fd_pr__nfet_01v8_lvt | W=0.84/L=0.15 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 170 | FETModules!B176 | nthin_lvt/22_2 | sky130_fd_pr__nfet_01v8_lvt | W=1/L=0.15 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 171 | FETModules!B177 | nthin_lvt/22_3 | sky130_fd_pr__nfet_01v8_lvt | W=1/L=0.18 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 172 | FETModules!B178 | nthin_lvt/22_4 | sky130_fd_pr__nfet_01v8_lvt | W=1/L=0.25 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 173 | FETModules!B179 | nthin_lvt/22_5 | sky130_fd_pr__nfet_01v8_lvt | W=1/L=0.5 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 174 | FETModules!B180 | nthin_lvt/22_6 | sky130_fd_pr__nfet_01v8_lvt | W=1/L=1 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 175 | FETModules!B181 | nthin_lvt/22_7 | sky130_fd_pr__nfet_01v8_lvt | W=1/L=2 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 176 | FETModules!B182 | nthin_lvt/22_8 | sky130_fd_pr__nfet_01v8_lvt | W=1/L=4 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 177 | FETModules!B183 | nthin_lvt/23_1 | sky130_fd_pr__nfet_01v8_lvt | W=1/L=8 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 178 | FETModules!B184 | nthin_lvt/23_2 | sky130_fd_pr__nfet_01v8_lvt | W=1.65/L=0.15 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 179 | FETModules!B185 | nthin_lvt/23_3 | sky130_fd_pr__nfet_01v8_lvt | W=1.65/L=0.18 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 180 | FETModules!B186 | nthin_lvt/23_4 | sky130_fd_pr__nfet_01v8_lvt | W=1.65/L=0.25 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 181 | FETModules!B187 | nthin_lvt/23_5 | sky130_fd_pr__nfet_01v8_lvt | W=1.65/L=0.5 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 182 | FETModules!B188 | nthin_lvt/23_6 | sky130_fd_pr__nfet_01v8_lvt | W=1.65/L=1 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 183 | FETModules!B189 | nthin_lvt/23_7 | sky130_fd_pr__nfet_01v8_lvt | W=1.65/L=2 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 184 | FETModules!B190 | nthin_lvt/23_8 | sky130_fd_pr__nfet_01v8_lvt | W=1.65/L=8 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 185 | FETModules!B191 | nthin_lvt/24_1 | sky130_fd_pr__nfet_01v8_lvt | W=3/L=0.15 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 186 | FETModules!B192 | nthin_lvt/24_2 | sky130_fd_pr__nfet_01v8_lvt | W=3/L=0.18 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 187 | FETModules!B193 | nthin_lvt/24_3 | sky130_fd_pr__nfet_01v8_lvt | W=3/L=0.25 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 188 | FETModules!B194 | nthin_lvt/24_4 | sky130_fd_pr__nfet_01v8_lvt | W=3/L=0.5 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 189 | FETModules!B195 | nthin_lvt/24_5 | sky130_fd_pr__nfet_01v8_lvt | W=3/L=1 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 190 | FETModules!B196 | nthin_lvt/24_6 | sky130_fd_pr__nfet_01v8_lvt | W=3/L=2 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 191 | FETModules!B197 | nthin_lvt/24_7 | sky130_fd_pr__nfet_01v8_lvt | W=3/L=4 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 192 | FETModules!B198 | nthin_lvt/24_8 | sky130_fd_pr__nfet_01v8_lvt | W=3/L=8 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 193 | FETModules!B199 | nthin_lvt/25_1 | sky130_fd_pr__nfet_01v8_lvt | W=3.01/L=0.15 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 194 | FETModules!B200 | nthin_lvt/25_2 | sky130_fd_pr__nfet_01v8_lvt | W=5/L=0.15 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 195 | FETModules!B201 | nthin_lvt/25_3 | sky130_fd_pr__nfet_01v8_lvt | W=5/L=0.18 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 196 | FETModules!B202 | nthin_lvt/25_4 | sky130_fd_pr__nfet_01v8_lvt | W=5/L=0.25 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 197 | FETModules!B203 | nthin_lvt/25_5 | sky130_fd_pr__nfet_01v8_lvt | W=5/L=0.5 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 198 | FETModules!B204 | nthin_lvt/25_6 | sky130_fd_pr__nfet_01v8_lvt | W=5/L=1 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 199 | FETModules!B205 | nthin_lvt/25_7 | sky130_fd_pr__nfet_01v8_lvt | W=5/L=2 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 200 | FETModules!B206 | nthin_lvt/25_8 | sky130_fd_pr__nfet_01v8_lvt | W=5/L=4 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 201 | FETModules!B207 | nthin_lvt/26_1 | sky130_fd_pr__nfet_01v8_lvt | W=5/L=8 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 202 | FETModules!B208 | nthin_lvt/26_2 | sky130_fd_pr__nfet_01v8_lvt | W=7/L=0.15 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 203 | FETModules!B209 | nthin_lvt/26_3 | sky130_fd_pr__nfet_01v8_lvt | W=7/L=0.18 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 204 | FETModules!B210 | nthin_lvt/26_4 | sky130_fd_pr__nfet_01v8_lvt | W=7/L=0.25 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 205 | FETModules!B211 | nthin_lvt/26_5 | sky130_fd_pr__nfet_01v8_lvt | W=7/L=0.5 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 206 | FETModules!B212 | nthin_lvt/26_6 | sky130_fd_pr__nfet_01v8_lvt | W=7/L=1 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 207 | FETModules!B213 | nthin_lvt/26_7 | sky130_fd_pr__nfet_01v8_lvt | W=7/L=2 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 208 | FETModules!B214 | nthin_lvt/26_8 | sky130_fd_pr__nfet_01v8_lvt | W=7/L=8 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 209 | FETModules!B217 | pthin_lvt/27_1 | sky130_fd_pr__pfet_01v8_lvt | W=0.42/L=0.35 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 210 | FETModules!B218 | pthin_lvt/27_2 | sky130_fd_pr__pfet_01v8_lvt | W=0.42/L=0.5 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 211 | FETModules!B219 | pthin_lvt/27_3 | sky130_fd_pr__pfet_01v8_lvt | W=0.42/L=1 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 212 | FETModules!B220 | pthin_lvt/27_4 | sky130_fd_pr__pfet_01v8_lvt | W=0.42/L=2 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 213 | FETModules!B221 | pthin_lvt/27_5 | sky130_fd_pr__pfet_01v8_lvt | W=0.42/L=4 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 214 | FETModules!B222 | pthin_lvt/27_6 | sky130_fd_pr__pfet_01v8_lvt | W=0.42/L=8 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 215 | FETModules!B223 | pthin_lvt/27_7 | sky130_fd_pr__pfet_01v8_lvt | W=0.42/L=20 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 216 | FETModules!B224 | pthin_lvt/27_8 | sky130_fd_pr__pfet_01v8_lvt | W=0.55/L=0.35 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 217 | FETModules!B225 | pthin_lvt/28_1 | sky130_fd_pr__pfet_01v8_lvt | W=0.55/L=0.5 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 218 | FETModules!B226 | pthin_lvt/28_2 | sky130_fd_pr__pfet_01v8_lvt | W=0.55/L=1 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 219 | FETModules!B227 | pthin_lvt/28_3 | sky130_fd_pr__pfet_01v8_lvt | W=0.55/L=2 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 220 | FETModules!B228 | pthin_lvt/28_4 | sky130_fd_pr__pfet_01v8_lvt | W=0.55/L=4 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 221 | FETModules!B229 | pthin_lvt/28_5 | sky130_fd_pr__pfet_01v8_lvt | W=0.55/L=8 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 222 | FETModules!B230 | pthin_lvt/28_6 | sky130_fd_pr__pfet_01v8_lvt | W=1/L=0.35 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 223 | FETModules!B231 | pthin_lvt/28_7 | sky130_fd_pr__pfet_01v8_lvt | W=1/L=0.5 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 224 | FETModules!B232 | pthin_lvt/28_8 | sky130_fd_pr__pfet_01v8_lvt | W=1/L=1 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 225 | FETModules!B233 | pthin_lvt/29_1 | sky130_fd_pr__pfet_01v8_lvt | W=1/L=2 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 226 | FETModules!B234 | pthin_lvt/29_2 | sky130_fd_pr__pfet_01v8_lvt | W=1/L=4 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 227 | FETModules!B235 | pthin_lvt/29_3 | sky130_fd_pr__pfet_01v8_lvt | W=1/L=8 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 228 | FETModules!B236 | pthin_lvt/29_4 | sky130_fd_pr__pfet_01v8_lvt | W=1/L=20 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 229 | FETModules!B237 | pthin_lvt/29_5 | sky130_fd_pr__pfet_01v8_lvt | W=3/L=0.35 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 230 | FETModules!B238 | pthin_lvt/29_6 | sky130_fd_pr__pfet_01v8_lvt | W=3/L=1 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 231 | FETModules!B239 | pthin_lvt/29_7 | sky130_fd_pr__pfet_01v8_lvt | W=3/L=1.5 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 232 | FETModules!B240 | pthin_lvt/29_8 | sky130_fd_pr__pfet_01v8_lvt | W=3/L=2 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 233 | FETModules!B241 | pthin_lvt/30_1 | sky130_fd_pr__pfet_01v8_lvt | W=3/L=4 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 234 | FETModules!B242 | pthin_lvt/30_2 | sky130_fd_pr__pfet_01v8_lvt | W=3/L=8 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 235 | FETModules!B243 | pthin_lvt/30_3 | sky130_fd_pr__pfet_01v8_lvt | W=5/L=0.35 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 236 | FETModules!B244 | pthin_lvt/30_4 | sky130_fd_pr__pfet_01v8_lvt | W=5/L=0.5 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 237 | FETModules!B245 | pthin_lvt/30_5 | sky130_fd_pr__pfet_01v8_lvt | W=5/L=1 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 238 | FETModules!B246 | pthin_lvt/30_6 | sky130_fd_pr__pfet_01v8_lvt | W=5/L=1.5 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 239 | FETModules!B247 | pthin_lvt/30_7 | sky130_fd_pr__pfet_01v8_lvt | W=5/L=2 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 240 | FETModules!B248 | pthin_lvt/30_8 | sky130_fd_pr__pfet_01v8_lvt | W=5/L=4 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 241 | FETModules!B249 | pthin_lvt/31_1 | sky130_fd_pr__pfet_01v8_lvt | W=5/L=8 | 1=B 2=G 3=S 4=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 242 | FETModules!B250 | pthin_lvt/31_2 | sky130_fd_pr__pfet_01v8_lvt | W=7/L=0.35 | 1=B 2=G 4=S 5=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 243 | FETModules!B251 | pthin_lvt/31_3 | sky130_fd_pr__pfet_01v8_lvt | W=7/L=0.5 | 1=B 2=G 5=S 6=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 244 | FETModules!B252 | pthin_lvt/31_4 | sky130_fd_pr__pfet_01v8_lvt | W=7/L=1 | 1=B 2=G 6=S 7=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 245 | FETModules!B253 | pthin_lvt/31_5 | sky130_fd_pr__pfet_01v8_lvt | W=7/L=1.5 | 1=B 2=G 7=S 8=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 246 | FETModules!B254 | pthin_lvt/31_6 | sky130_fd_pr__pfet_01v8_lvt | W=7/L=2 | 1=B 2=G 8=S 9=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 247 | FETModules!B255 | pthin_lvt/31_7 | sky130_fd_pr__pfet_01v8_lvt | W=7/L=8 | 1=B 2=G 9=S 10=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 248 | FETModules!B256 | pthin_lvt/31_8 | sky130_fd_pr__pfet_01v8_lvt | W=7/L=20 | 1=B 2=G 10=S 11=D | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 249 | FETModules!B259 | nthick/32_1 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5/L=0.42 | 1=B 2=G 3=S 4=D | nfet_06v0, 0.5 × 0.7, nf=1; single device in addressed array |
| 250 | FETModules!B260 | nthick/32_2 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5/L=0.75 | 1=B 2=G 4=S 5=D | nfet_06v0, 0.5 × 1.03, nf=1; single device in addressed array |
| 251 | FETModules!B261 | nthick/32_3 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5/L=1 | 1=B 2=G 5=S 6=D | nfet_06v0, 0.5 × 1.28, nf=1; single device in addressed array |
| 252 | FETModules!B262 | nthick/32_4 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5/L=1.5 | 1=B 2=G 6=S 7=D | nfet_06v0, 0.5 × 1.78, nf=1; single device in addressed array |
| 253 | FETModules!B263 | nthick/32_5 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5/L=3 | 1=B 2=G 7=S 8=D | nfet_06v0, 0.5 × 3.28, nf=1; single device in addressed array |
| 254 | FETModules!B264 | nthick/32_6 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5/L=5 | 1=B 2=G 8=S 9=D | nfet_06v0, 0.5 × 5.28, nf=1; single device in addressed array |
| 255 | FETModules!B265 | nthick/32_7 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5/L=7 | 1=B 2=G 9=S 10=D | nfet_06v0, 0.5 × 7.28, nf=1; single device in addressed array |
| 256 | FETModules!B266 | nthick/32_8 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5/L=10 | 1=B 2=G 10=S 11=D | nfet_06v0, 0.5 × 10.28, nf=1; single device in addressed array |
| 257 | FETModules!B267 | nthick/33_1 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5/L=15 | 1=B 2=G 3=S 4=D | nfet_06v0, 0.5 × 15.28, nf=1; single device in addressed array |
| 258 | FETModules!B268 | nthick/33_2 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5/L=20 | 1=B 2=G 4=S 5=D | nfet_06v0, 0.5 × 20.28, nf=1; single device in addressed array |
| 259 | FETModules!B269 | nthick/33_3 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.6/L=0.42 | 1=B 2=G 5=S 6=D | nfet_06v0, 0.6 × 0.7, nf=1; single device in addressed array |
| 260 | FETModules!B270 | nthick/33_4 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.6/L=0.7 | 1=B 2=G 6=S 7=D | nfet_06v0, 0.6 × 0.98, nf=1; single device in addressed array |
| 261 | FETModules!B271 | nthick/33_5 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.6/L=1 | 1=B 2=G 7=S 8=D | nfet_06v0, 0.6 × 1.28, nf=1; single device in addressed array |
| 262 | FETModules!B272 | nthick/33_6 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.6/L=3 | 1=B 2=G 8=S 9=D | nfet_06v0, 0.6 × 3.28, nf=1; single device in addressed array |
| 263 | FETModules!B273 | nthick/33_7 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.6/L=5 | 1=B 2=G 9=S 10=D | nfet_06v0, 0.6 × 5.28, nf=1; single device in addressed array |
| 264 | FETModules!B274 | nthick/33_8 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.6/L=15 | 1=B 2=G 10=S 11=D | nfet_06v0, 0.6 × 15.28, nf=1; single device in addressed array |
| 265 | FETModules!B275 | nthick/34_1 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.6/L=20 | 1=B 2=G 3=S 4=D | nfet_06v0, 0.6 × 20.28, nf=1; single device in addressed array |
| 266 | FETModules!B276 | nthick/34_2 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.8/L=0.42 | 1=B 2=G 4=S 5=D | nfet_06v0, 0.8 × 0.7, nf=1; single device in addressed array |
| 267 | FETModules!B277 | nthick/34_3 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.8/L=0.75 | 1=B 2=G 5=S 6=D | nfet_06v0, 0.8 × 1.03, nf=1; single device in addressed array |
| 268 | FETModules!B278 | nthick/34_4 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.8/L=1 | 1=B 2=G 6=S 7=D | nfet_06v0, 0.8 × 1.28, nf=1; single device in addressed array |
| 269 | FETModules!B279 | nthick/34_5 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.8/L=1.5 | 1=B 2=G 7=S 8=D | nfet_06v0, 0.8 × 1.78, nf=1; single device in addressed array |
| 270 | FETModules!B280 | nthick/34_6 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.8/L=5 | 1=B 2=G 8=S 9=D | nfet_06v0, 0.8 × 5.28, nf=1; single device in addressed array |
| 271 | FETModules!B281 | nthick/34_7 | sky130_fd_pr__nfet_g5v0d10v5 | W=1/L=0.42 | 1=B 2=G 9=S 10=D | nfet_06v0, 1 × 0.7, nf=1; single device in addressed array |
| 272 | FETModules!B282 | nthick/34_8 | sky130_fd_pr__nfet_g5v0d10v5 | W=1/L=0.75 | 1=B 2=G 10=S 11=D | nfet_06v0, 1 × 1.03, nf=1; single device in addressed array |
| 273 | FETModules!B283 | nthick/35_1 | sky130_fd_pr__nfet_g5v0d10v5 | W=1/L=1 | 1=B 2=G 3=S 4=D | nfet_06v0, 1 × 1.28, nf=1; single device in addressed array |
| 274 | FETModules!B284 | nthick/35_2 | sky130_fd_pr__nfet_g5v0d10v5 | W=1/L=1.5 | 1=B 2=G 4=S 5=D | nfet_06v0, 1 × 1.78, nf=1; single device in addressed array |
| 275 | FETModules!B285 | nthick/35_3 | sky130_fd_pr__nfet_g5v0d10v5 | W=1/L=3 | 1=B 2=G 5=S 6=D | nfet_06v0, 1 × 3.28, nf=1; single device in addressed array |
| 276 | FETModules!B286 | nthick/35_4 | sky130_fd_pr__nfet_g5v0d10v5 | W=1/L=5 | 1=B 2=G 6=S 7=D | nfet_06v0, 1 × 5.28, nf=1; single device in addressed array |
| 277 | FETModules!B287 | nthick/35_5 | sky130_fd_pr__nfet_g5v0d10v5 | W=1/L=7 | 1=B 2=G 7=S 8=D | nfet_06v0, 1 × 7.28, nf=1; single device in addressed array |
| 278 | FETModules!B288 | nthick/35_6 | sky130_fd_pr__nfet_g5v0d10v5 | W=1/L=10 | 1=B 2=G 8=S 9=D | nfet_06v0, 1 × 10.28, nf=1; single device in addressed array |
| 279 | FETModules!B289 | nthick/35_7 | sky130_fd_pr__nfet_g5v0d10v5 | W=1/L=20 | 1=B 2=G 9=S 10=D | nfet_06v0, 1 × 20.28, nf=1; single device in addressed array |
| 280 | FETModules!B290 | nthick/35_8 | sky130_fd_pr__nfet_g5v0d10v5 | W=2/L=0.42 | 1=B 2=G 10=S 11=D | nfet_06v0, 2 × 0.7, nf=1; single device in addressed array |
| 281 | FETModules!B291 | nthick/36_1 | sky130_fd_pr__nfet_g5v0d10v5 | W=2/L=0.75 | 1=B 2=G 3=S 4=D | nfet_06v0, 2 × 1.03, nf=1; single device in addressed array |
| 282 | FETModules!B292 | nthick/36_2 | sky130_fd_pr__nfet_g5v0d10v5 | W=2/L=1 | 1=B 2=G 4=S 5=D | nfet_06v0, 2 × 1.28, nf=1; single device in addressed array |
| 283 | FETModules!B293 | nthick/36_3 | sky130_fd_pr__nfet_g5v0d10v5 | W=2/L=1.5 | 1=B 2=G 5=S 6=D | nfet_06v0, 2 × 1.78, nf=1; single device in addressed array |
| 284 | FETModules!B294 | nthick/36_4 | sky130_fd_pr__nfet_g5v0d10v5 | W=2/L=3 | 1=B 2=G 6=S 7=D | nfet_06v0, 2 × 3.28, nf=1; single device in addressed array |
| 285 | FETModules!B295 | nthick/36_5 | sky130_fd_pr__nfet_g5v0d10v5 | W=2/L=5 | 1=B 2=G 7=S 8=D | nfet_06v0, 2 × 5.28, nf=1; single device in addressed array |
| 286 | FETModules!B296 | nthick/36_6 | sky130_fd_pr__nfet_g5v0d10v5 | W=2/L=7 | 1=B 2=G 8=S 9=D | nfet_06v0, 2 × 7.28, nf=1; single device in addressed array |
| 287 | FETModules!B297 | nthick/36_7 | sky130_fd_pr__nfet_g5v0d10v5 | W=4/L=0.42 | 1=B 2=G 9=S 10=D | nfet_06v0, 4 × 0.7, nf=1; single device in addressed array |
| 288 | FETModules!B298 | nthick/36_8 | sky130_fd_pr__nfet_g5v0d10v5 | W=4/L=0.75 | 1=B 2=G 10=S 11=D | nfet_06v0, 4 × 1.03, nf=1; single device in addressed array |
| 289 | FETModules!B299 | nthick/37_1 | sky130_fd_pr__nfet_g5v0d10v5 | W=4/L=1 | 1=B 2=G 3=S 4=D | nfet_06v0, 4 × 1.28, nf=1; single device in addressed array |
| 290 | FETModules!B300 | nthick/37_2 | sky130_fd_pr__nfet_g5v0d10v5 | W=4/L=1.5 | 1=B 2=G 4=S 5=D | nfet_06v0, 4 × 1.78, nf=1; single device in addressed array |
| 291 | FETModules!B301 | nthick/37_3 | sky130_fd_pr__nfet_g5v0d10v5 | W=4/L=3 | 1=B 2=G 5=S 6=D | nfet_06v0, 4 × 3.28, nf=1; single device in addressed array |
| 292 | FETModules!B302 | nthick/37_4 | sky130_fd_pr__nfet_g5v0d10v5 | W=4/L=5 | 1=B 2=G 6=S 7=D | nfet_06v0, 4 × 5.28, nf=1; single device in addressed array |
| 293 | FETModules!B303 | nthick/37_5 | sky130_fd_pr__nfet_g5v0d10v5 | W=4/L=7 | 1=B 2=G 7=S 8=D | nfet_06v0, 4 × 7.28, nf=1; single device in addressed array |
| 294 | FETModules!B304 | nthick/37_6 | sky130_fd_pr__nfet_g5v0d10v5 | W=8/L=0.42 | 1=B 2=G 8=S 9=D | nfet_06v0, 8 × 0.7, nf=1; single device in addressed array |
| 295 | FETModules!B305 | nthick/37_7 | sky130_fd_pr__nfet_g5v0d10v5 | W=8/L=1 | 1=B 2=G 9=S 10=D | nfet_06v0, 8 × 1.28, nf=1; single device in addressed array |
| 296 | FETModules!B306 | nthick/37_8 | sky130_fd_pr__nfet_g5v0d10v5 | W=8/L=3 | 1=B 2=G 10=S 11=D | nfet_06v0, 8 × 3.28, nf=1; single device in addressed array |
| 297 | FETModules!B307 | nthick/38_1 | sky130_fd_pr__nfet_g5v0d10v5 | W=8/L=5 | 1=B 2=G 3=S 4=D | nfet_06v0, 8 × 5.28, nf=1; single device in addressed array |
| 298 | FETModules!B308 | nthick/38_2 | sky130_fd_pr__nfet_g5v0d10v5 | W=8/L=7 | 1=B 2=G 4=S 5=D | nfet_06v0, 8 × 7.28, nf=1; single device in addressed array |
| 299 | FETModules!B309 | nthick/38_3 | sky130_fd_pr__nfet_g5v0d10v5 | W=8/L=10 | 1=B 2=G 5=S 6=D | nfet_06v0, 8 × 10.28, nf=1; single device in addressed array |
| 300 | FETModules!B310 | nthick/38_4 | sky130_fd_pr__nfet_g5v0d10v5 | W=8/L=20 | 1=B 2=G 6=S 7=D | nfet_06v0, 8 × 20.28, nf=1; single device in addressed array |
| 301 | FETModules!B311 | nthick/38_5 | sky130_fd_pr__nfet_g5v0d10v5 | W=20/L=0.42 | 1=B 2=G 7=S 8=D | nfet_06v0, 20 × 0.7, nf=1; single device in addressed array |
| 302 | FETModules!B312 | nthick/38_6 | sky130_fd_pr__nfet_g5v0d10v5 | W=20/L=1.5 | 1=B 2=G 8=S 9=D | nfet_06v0, 20 × 1.78, nf=1; single device in addressed array |
| 303 | FETModules!B313 | nthick/38_7 | sky130_fd_pr__nfet_g5v0d10v5 | W=20/L=10 | 1=B 2=G 9=S 10=D | nfet_06v0, 20 × 10.28, nf=1; single device in addressed array |
| 304 | FETModules!B314 | nthick/38_8 | sky130_fd_pr__nfet_g5v0d10v5 | W=20/L=20 | 1=B 2=G 10=S 11=D | nfet_06v0, 20 × 20.28, nf=1; single device in addressed array |
| 305 | FETModules!B317 | pthick/39_1 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5/L=0.42 | 1=B 2=G 3=S 4=D | pfet_06v0, 0.5 × 0.55, nf=1; single device in addressed array |
| 306 | FETModules!B318 | pthick/39_2 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5/L=0.75 | 1=B 2=G 4=S 5=D | pfet_06v0, 0.5 × 0.88, nf=1; single device in addressed array |
| 307 | FETModules!B319 | pthick/39_3 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5/L=1 | 1=B 2=G 5=S 6=D | pfet_06v0, 0.5 × 1.13, nf=1; single device in addressed array |
| 308 | FETModules!B320 | pthick/39_4 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5/L=1.5 | 1=B 2=G 6=S 7=D | pfet_06v0, 0.5 × 1.63, nf=1; single device in addressed array |
| 309 | FETModules!B321 | pthick/39_5 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5/L=3 | 1=B 2=G 7=S 8=D | pfet_06v0, 0.5 × 3.13, nf=1; single device in addressed array |
| 310 | FETModules!B322 | pthick/39_6 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5/L=5 | 1=B 2=G 8=S 9=D | pfet_06v0, 0.5 × 5.13, nf=1; single device in addressed array |
| 311 | FETModules!B323 | pthick/39_7 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5/L=7 | 1=B 2=G 9=S 10=D | pfet_06v0, 0.5 × 7.13, nf=1; single device in addressed array |
| 312 | FETModules!B324 | pthick/39_8 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5/L=10 | 1=B 2=G 10=S 11=D | pfet_06v0, 0.5 × 10.13, nf=1; single device in addressed array |
| 313 | FETModules!B325 | pthick/40_1 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5/L=15 | 1=B 2=G 3=S 4=D | pfet_06v0, 0.5 × 15.13, nf=1; single device in addressed array |
| 314 | FETModules!B326 | pthick/40_2 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5/L=20 | 1=B 2=G 4=S 5=D | pfet_06v0, 0.5 × 20.13, nf=1; single device in addressed array |
| 315 | FETModules!B327 | pthick/40_3 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.6/L=0.42 | 1=B 2=G 5=S 6=D | pfet_06v0, 0.6 × 0.55, nf=1; single device in addressed array |
| 316 | FETModules!B328 | pthick/40_4 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.6/L=0.7 | 1=B 2=G 6=S 7=D | pfet_06v0, 0.6 × 0.83, nf=1; single device in addressed array |
| 317 | FETModules!B329 | pthick/40_5 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.6/L=1 | 1=B 2=G 7=S 8=D | pfet_06v0, 0.6 × 1.13, nf=1; single device in addressed array |
| 318 | FETModules!B330 | pthick/40_6 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.6/L=3 | 1=B 2=G 8=S 9=D | pfet_06v0, 0.6 × 3.13, nf=1; single device in addressed array |
| 319 | FETModules!B331 | pthick/40_7 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.6/L=5 | 1=B 2=G 9=S 10=D | pfet_06v0, 0.6 × 5.13, nf=1; single device in addressed array |
| 320 | FETModules!B332 | pthick/40_8 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.6/L=15 | 1=B 2=G 10=S 11=D | pfet_06v0, 0.6 × 15.13, nf=1; single device in addressed array |
| 321 | FETModules!B333 | pthick/41_1 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.6/L=20 | 1=B 2=G 3=S 4=D | pfet_06v0, 0.6 × 20.13, nf=1; single device in addressed array |
| 322 | FETModules!B334 | pthick/41_2 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.8/L=0.42 | 1=B 2=G 4=S 5=D | pfet_06v0, 0.8 × 0.55, nf=1; single device in addressed array |
| 323 | FETModules!B335 | pthick/41_3 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.8/L=0.75 | 1=B 2=G 5=S 6=D | pfet_06v0, 0.8 × 0.88, nf=1; single device in addressed array |
| 324 | FETModules!B336 | pthick/41_4 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.8/L=1 | 1=B 2=G 6=S 7=D | pfet_06v0, 0.8 × 1.13, nf=1; single device in addressed array |
| 325 | FETModules!B337 | pthick/41_5 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.8/L=5 | 1=B 2=G 7=S 8=D | pfet_06v0, 0.8 × 5.13, nf=1; single device in addressed array |
| 326 | FETModules!B338 | pthick/41_6 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.8/L=7 | 1=B 2=G 8=S 9=D | pfet_06v0, 0.8 × 7.13, nf=1; single device in addressed array |
| 327 | FETModules!B339 | pthick/41_7 | sky130_fd_pr__pfet_g5v0d10v5 | W=1/L=0.42 | 1=B 2=G 9=S 10=D | pfet_06v0, 1 × 0.55, nf=1; single device in addressed array |
| 328 | FETModules!B340 | pthick/41_8 | sky130_fd_pr__pfet_g5v0d10v5 | W=1/L=0.75 | 1=B 2=G 10=S 11=D | pfet_06v0, 1 × 0.88, nf=1; single device in addressed array |
| 329 | FETModules!B341 | pthick/42_1 | sky130_fd_pr__pfet_g5v0d10v5 | W=1/L=1 | 1=B 2=G 3=S 4=D | pfet_06v0, 1 × 1.13, nf=1; single device in addressed array |
| 330 | FETModules!B342 | pthick/42_2 | sky130_fd_pr__pfet_g5v0d10v5 | W=1/L=1.5 | 1=B 2=G 4=S 5=D | pfet_06v0, 1 × 1.63, nf=1; single device in addressed array |
| 331 | FETModules!B343 | pthick/42_3 | sky130_fd_pr__pfet_g5v0d10v5 | W=1/L=3 | 1=B 2=G 5=S 6=D | pfet_06v0, 1 × 3.13, nf=1; single device in addressed array |
| 332 | FETModules!B344 | pthick/42_4 | sky130_fd_pr__pfet_g5v0d10v5 | W=1/L=5 | 1=B 2=G 6=S 7=D | pfet_06v0, 1 × 5.13, nf=1; single device in addressed array |
| 333 | FETModules!B345 | pthick/42_5 | sky130_fd_pr__pfet_g5v0d10v5 | W=1/L=7 | 1=B 2=G 7=S 8=D | pfet_06v0, 1 × 7.13, nf=1; single device in addressed array |
| 334 | FETModules!B346 | pthick/42_6 | sky130_fd_pr__pfet_g5v0d10v5 | W=1/L=10 | 1=B 2=G 8=S 9=D | pfet_06v0, 1 × 10.13, nf=1; single device in addressed array |
| 335 | FETModules!B347 | pthick/42_7 | sky130_fd_pr__pfet_g5v0d10v5 | W=1/L=20 | 1=B 2=G 9=S 10=D | pfet_06v0, 1 × 20.13, nf=1; single device in addressed array |
| 336 | FETModules!B348 | pthick/42_8 | sky130_fd_pr__pfet_g5v0d10v5 | W=2/L=0.42 | 1=B 2=G 10=S 11=D | pfet_06v0, 2 × 0.55, nf=1; single device in addressed array |
| 337 | FETModules!B349 | pthick/43_1 | sky130_fd_pr__pfet_g5v0d10v5 | W=2/L=0.75 | 1=B 2=G 3=S 4=D | pfet_06v0, 2 × 0.88, nf=1; single device in addressed array |
| 338 | FETModules!B350 | pthick/43_2 | sky130_fd_pr__pfet_g5v0d10v5 | W=2/L=1 | 1=B 2=G 4=S 5=D | pfet_06v0, 2 × 1.13, nf=1; single device in addressed array |
| 339 | FETModules!B351 | pthick/43_3 | sky130_fd_pr__pfet_g5v0d10v5 | W=2/L=1.5 | 1=B 2=G 5=S 6=D | pfet_06v0, 2 × 1.63, nf=1; single device in addressed array |
| 340 | FETModules!B352 | pthick/43_4 | sky130_fd_pr__pfet_g5v0d10v5 | W=2/L=3 | 1=B 2=G 6=S 7=D | pfet_06v0, 2 × 3.13, nf=1; single device in addressed array |
| 341 | FETModules!B353 | pthick/43_5 | sky130_fd_pr__pfet_g5v0d10v5 | W=2/L=5 | 1=B 2=G 7=S 8=D | pfet_06v0, 2 × 5.13, nf=1; single device in addressed array |
| 342 | FETModules!B354 | pthick/43_6 | sky130_fd_pr__pfet_g5v0d10v5 | W=2/L=7 | 1=B 2=G 8=S 9=D | pfet_06v0, 2 × 7.13, nf=1; single device in addressed array |
| 343 | FETModules!B355 | pthick/43_7 | sky130_fd_pr__pfet_g5v0d10v5 | W=4/L=0.42 | 1=B 2=G 9=S 10=D | pfet_06v0, 4 × 0.55, nf=1; single device in addressed array |
| 344 | FETModules!B356 | pthick/43_8 | sky130_fd_pr__pfet_g5v0d10v5 | W=4/L=0.75 | 1=B 2=G 10=S 11=D | pfet_06v0, 4 × 0.88, nf=1; single device in addressed array |
| 345 | FETModules!B357 | pthick/44_1 | sky130_fd_pr__pfet_g5v0d10v5 | W=4/L=1.5 | 1=B 2=G 3=S 4=D | pfet_06v0, 4 × 1.63, nf=1; single device in addressed array |
| 346 | FETModules!B358 | pthick/44_2 | sky130_fd_pr__pfet_g5v0d10v5 | W=4/L=3 | 1=B 2=G 4=S 5=D | pfet_06v0, 4 × 3.13, nf=1; single device in addressed array |
| 347 | FETModules!B359 | pthick/44_3 | sky130_fd_pr__pfet_g5v0d10v5 | W=4/L=5 | 1=B 2=G 5=S 6=D | pfet_06v0, 4 × 5.13, nf=1; single device in addressed array |
| 348 | FETModules!B360 | pthick/44_4 | sky130_fd_pr__pfet_g5v0d10v5 | W=4/L=7 | 1=B 2=G 6=S 7=D | pfet_06v0, 4 × 7.13, nf=1; single device in addressed array |
| 349 | FETModules!B361 | pthick/44_5 | sky130_fd_pr__pfet_g5v0d10v5 | W=8/L=0.42 | 1=B 2=G 7=S 8=D | pfet_06v0, 8 × 0.55, nf=1; single device in addressed array |
| 350 | FETModules!B362 | pthick/44_6 | sky130_fd_pr__pfet_g5v0d10v5 | W=8/L=1 | 1=B 2=G 8=S 9=D | pfet_06v0, 8 × 1.13, nf=1; single device in addressed array |
| 351 | FETModules!B363 | pthick/44_7 | sky130_fd_pr__pfet_g5v0d10v5 | W=8/L=3 | 1=B 2=G 9=S 10=D | pfet_06v0, 8 × 3.13, nf=1; single device in addressed array |
| 352 | FETModules!B364 | pthick/44_8 | sky130_fd_pr__pfet_g5v0d10v5 | W=8/L=5 | 1=B 2=G 10=S 11=D | pfet_06v0, 8 × 5.13, nf=1; single device in addressed array |
| 353 | FETModules!B365 | pthick/45_1 | sky130_fd_pr__pfet_g5v0d10v5 | W=8/L=7 | 1=B 2=G 3=S 4=D | pfet_06v0, 8 × 7.13, nf=1; single device in addressed array |
| 354 | FETModules!B366 | pthick/45_2 | sky130_fd_pr__pfet_g5v0d10v5 | W=8/L=10 | 1=B 2=G 4=S 5=D | pfet_06v0, 8 × 10.13, nf=1; single device in addressed array |
| 355 | FETModules!B367 | pthick/45_3 | sky130_fd_pr__pfet_g5v0d10v5 | W=8/L=20 | 1=B 2=G 5=S 6=D | pfet_06v0, 8 × 20.13, nf=1; single device in addressed array |
| 356 | FETModules!B368 | pthick/45_4 | sky130_fd_pr__pfet_g5v0d10v5 | W=20/L=0.42 | 1=B 2=G 6=S 7=D | pfet_06v0, 20 × 0.55, nf=1; single device in addressed array |
| 357 | FETModules!B369 | pthick/45_5 | sky130_fd_pr__pfet_g5v0d10v5 | W=20/L=1 | 1=B 2=G 7=S 8=D | pfet_06v0, 20 × 1.13, nf=1; single device in addressed array |
| 358 | FETModules!B370 | pthick/45_6 | sky130_fd_pr__pfet_g5v0d10v5 | W=20/L=5 | 1=B 2=G 8=S 9=D | pfet_06v0, 20 × 5.13, nf=1; single device in addressed array |
| 359 | FETModules!B371 | pthick/45_7 | sky130_fd_pr__pfet_g5v0d10v5 | W=20/L=10 | 1=B 2=G 9=S 10=D | pfet_06v0, 20 × 10.13, nf=1; single device in addressed array |
| 360 | FETModules!B372 | pthick/45_8 | sky130_fd_pr__pfet_g5v0d10v5 | W=20/L=20 | 1=B 2=G 10=S 11=D | pfet_06v0, 20 × 20.13, nf=1; single device in addressed array |
| 361 | FETModules!B375 | nnative/46_1 | sky130_fd_pr__nfet_03v3_nvt | W=0.5/L=0.42 | 1=B 2=G 3=S 4=D | nfet_06v0_nvt, 0.8 × 1.8, nf=1; single device in addressed array |
| 362 | FETModules!B376 | nnative/46_2 | sky130_fd_pr__nfet_03v3_nvt | W=0.5/L=0.7 | 1=B 2=G 4=S 5=D | nfet_06v0_nvt, 0.8 × 2.08, nf=1; single device in addressed array |
| 363 | FETModules!B377 | nnative/46_3 | sky130_fd_pr__nfet_03v3_nvt | W=0.5/L=1 | 1=B 2=G 5=S 6=D | nfet_06v0_nvt, 0.8 × 2.38, nf=1; single device in addressed array |
| 364 | FETModules!B378 | nnative/46_4 | sky130_fd_pr__nfet_03v3_nvt | W=0.5/L=2 | 1=B 2=G 6=S 7=D | nfet_06v0_nvt, 0.8 × 3.38, nf=1; single device in addressed array |
| 365 | FETModules!B379 | nnative/46_5 | sky130_fd_pr__nfet_03v3_nvt | W=0.5/L=4 | 1=B 2=G 7=S 8=D | nfet_06v0_nvt, 0.8 × 5.38, nf=1; single device in addressed array |
| 366 | FETModules!B380 | nnative/46_6 | sky130_fd_pr__nfet_03v3_nvt | W=0.5/L=8 | 1=B 2=G 8=S 9=D | nfet_06v0_nvt, 0.8 × 9.38, nf=1; single device in addressed array |
| 367 | FETModules!B381 | nnative/46_7 | sky130_fd_pr__nfet_03v3_nvt | W=0.5/L=20 | 1=B 2=G 9=S 10=D | nfet_06v0_nvt, 0.8 × 21.38, nf=1; single device in addressed array |
| 368 | FETModules!B382 | nnative/46_8 | sky130_fd_pr__nfet_03v3_nvt | W=0.6/L=0.42 | 1=B 2=G 10=S 11=D | nfet_06v0_nvt, 0.9 × 1.8, nf=1; single device in addressed array |
| 369 | FETModules!B383 | nnative/47_1 | sky130_fd_pr__nfet_03v3_nvt | W=0.6/L=0.7 | 1=B 2=G 3=S 4=D | nfet_06v0_nvt, 0.9 × 2.08, nf=1; single device in addressed array |
| 370 | FETModules!B384 | nnative/47_2 | sky130_fd_pr__nfet_03v3_nvt | W=0.6/L=1 | 1=B 2=G 4=S 5=D | nfet_06v0_nvt, 0.9 × 2.38, nf=1; single device in addressed array |
| 371 | FETModules!B385 | nnative/47_3 | sky130_fd_pr__nfet_03v3_nvt | W=0.6/L=2 | 1=B 2=G 5=S 6=D | nfet_06v0_nvt, 0.9 × 3.38, nf=1; single device in addressed array |
| 372 | FETModules!B386 | nnative/47_4 | sky130_fd_pr__nfet_03v3_nvt | W=0.6/L=4 | 1=B 2=G 6=S 7=D | nfet_06v0_nvt, 0.9 × 5.38, nf=1; single device in addressed array |
| 373 | FETModules!B387 | nnative/47_5 | sky130_fd_pr__nfet_03v3_nvt | W=0.6/L=8 | 1=B 2=G 7=S 8=D | nfet_06v0_nvt, 0.9 × 9.38, nf=1; single device in addressed array |
| 374 | FETModules!B388 | nnative/47_6 | sky130_fd_pr__nfet_03v3_nvt | W=0.8/L=0.42 | 1=B 2=G 8=S 9=D | nfet_06v0_nvt, 1.1 × 1.8, nf=1; single device in addressed array |
| 375 | FETModules!B389 | nnative/47_7 | sky130_fd_pr__nfet_03v3_nvt | W=0.8//L=0.7 | 1=B 2=G 9=S 10=D | nfet_06v0_nvt, 1.1 × 2.08, nf=1; single device in addressed array |
| 376 | FETModules!B390 | nnative/47_8 | sky130_fd_pr__nfet_03v3_nvt | W=0.8//L=1 | 1=B 2=G 10=S 11=D | nfet_06v0_nvt, 1.1 × 2.38, nf=1; single device in addressed array |
| 377 | FETModules!B391 | nnative/48_1 | sky130_fd_pr__nfet_03v3_nvt | W=0.8//L=2 | 1=B 2=G 3=S 4=D | nfet_06v0_nvt, 1.1 × 3.38, nf=1; single device in addressed array |
| 378 | FETModules!B392 | nnative/48_2 | sky130_fd_pr__nfet_03v3_nvt | W=0.8//L=4 | 1=B 2=G 4=S 5=D | nfet_06v0_nvt, 1.1 × 5.38, nf=1; single device in addressed array |
| 379 | FETModules!B393 | nnative/48_3 | sky130_fd_pr__nfet_03v3_nvt | W=0.8//L=8 | 1=B 2=G 5=S 6=D | nfet_06v0_nvt, 1.1 × 9.38, nf=1; single device in addressed array |
| 380 | FETModules!B394 | nnative/48_4 | sky130_fd_pr__nfet_03v3_nvt | W=0.8//L=20 | 1=B 2=G 6=S 7=D | nfet_06v0_nvt, 1.1 × 21.38, nf=1; single device in addressed array |
| 381 | FETModules!B395 | nnative/48_5 | sky130_fd_pr__nfet_03v3_nvt | W=1/L=0.42 | 1=B 2=G 7=S 8=D | nfet_06v0_nvt, 1.3 × 1.8, nf=1; single device in addressed array |
| 382 | FETModules!B396 | nnative/48_6 | sky130_fd_pr__nfet_03v3_nvt | W=1/L=1 | 1=B 2=G 8=S 9=D | nfet_06v0_nvt, 1.3 × 2.38, nf=1; single device in addressed array |
| 383 | FETModules!B397 | nnative/48_7 | sky130_fd_pr__nfet_03v3_nvt | W=1/L=1.5 | 1=B 2=G 9=S 10=D | nfet_06v0_nvt, 1.3 × 2.88, nf=1; single device in addressed array |
| 384 | FETModules!B398 | nnative/48_8 | sky130_fd_pr__nfet_03v3_nvt | W=1/L=2 | 1=B 2=G 10=S 11=D | nfet_06v0_nvt, 1.3 × 3.38, nf=1; single device in addressed array |
| 385 | FETModules!B399 | nnative/49_1 | sky130_fd_pr__nfet_03v3_nvt | W=1/L=4 | 1=B 2=G 3=S 4=D | nfet_06v0_nvt, 1.3 × 5.38, nf=1; single device in addressed array |
| 386 | FETModules!B400 | nnative/49_2 | sky130_fd_pr__nfet_03v3_nvt | W=1/L=8 | 1=B 2=G 4=S 5=D | nfet_06v0_nvt, 1.3 × 9.38, nf=1; single device in addressed array |
| 387 | FETModules!B401 | nnative/49_3 | sky130_fd_pr__nfet_03v3_nvt | W=5/L=0.42 | 1=B 2=G 5=S 6=D | nfet_06v0_nvt, 5.3 × 1.8, nf=1; single device in addressed array |
| 388 | FETModules!B402 | nnative/49_4 | sky130_fd_pr__nfet_03v3_nvt | W=5/L=0.7 | 1=B 2=G 6=S 7=D | nfet_06v0_nvt, 5.3 × 2.08, nf=1; single device in addressed array |
| 389 | FETModules!B403 | nnative/49_5 | sky130_fd_pr__nfet_03v3_nvt | W=5/L=1 | 1=B 2=G 7=S 8=D | nfet_06v0_nvt, 5.3 × 2.38, nf=1; single device in addressed array |
| 390 | FETModules!B404 | nnative/49_6 | sky130_fd_pr__nfet_03v3_nvt | W=5/L=1.5 | 1=B 2=G 8=S 9=D | nfet_06v0_nvt, 5.3 × 2.88, nf=1; single device in addressed array |
| 391 | FETModules!B405 | nnative/49_7 | sky130_fd_pr__nfet_03v3_nvt | W=5/L=2 | 1=B 2=G 9=S 10=D | nfet_06v0_nvt, 5.3 × 3.38, nf=1; single device in addressed array |
| 392 | FETModules!B406 | nnative/49_8 | sky130_fd_pr__nfet_03v3_nvt | W=5/L=4 | 1=B 2=G 10=S 11=D | nfet_06v0_nvt, 5.3 × 5.38, nf=1; single device in addressed array |
| 393 | FETModules!B407 | nnative/50_1 | sky130_fd_pr__nfet_03v3_nvt | W=5/L=8 | 1=B 2=G 3=S 4=D | nfet_06v0_nvt, 5.3 × 9.38, nf=1; single device in addressed array |
| 394 | FETModules!B408 | nnative/50_2 | sky130_fd_pr__nfet_03v3_nvt | W=7/L=0.42 | 1=B 2=G 4=S 5=D | nfet_06v0_nvt, 7.3 × 1.8, nf=1; single device in addressed array |
| 395 | FETModules!B409 | nnative/50_3 | sky130_fd_pr__nfet_03v3_nvt | W=7/L=0.5 | 1=B 2=G 5=S 6=D | nfet_06v0_nvt, 7.3 × 1.88, nf=1; single device in addressed array |
| 396 | FETModules!B410 | nnative/50_4 | sky130_fd_pr__nfet_03v3_nvt | W=7/L=1 | 1=B 2=G 6=S 7=D | nfet_06v0_nvt, 7.3 × 2.38, nf=1; single device in addressed array |
| 397 | FETModules!B411 | nnative/50_5 | sky130_fd_pr__nfet_03v3_nvt | W=7/L=1.5 | 1=B 2=G 7=S 8=D | nfet_06v0_nvt, 7.3 × 2.88, nf=1; single device in addressed array |
| 398 | FETModules!B412 | nnative/50_6 | sky130_fd_pr__nfet_03v3_nvt | W=7/L=2 | 1=B 2=G 8=S 9=D | nfet_06v0_nvt, 7.3 × 3.38, nf=1; single device in addressed array |
| 399 | FETModules!B413 | nnative/50_7 | sky130_fd_pr__nfet_03v3_nvt | W=7/L=8 | 1=B 2=G 9=S 10=D | nfet_06v0_nvt, 7.3 × 9.38, nf=1; single device in addressed array |
| 400 | FETModules!B414 | nnative/50_8 | sky130_fd_pr__nfet_03v3_nvt | W=7/L=20 | 1=B 2=G 10=S 11=D | nfet_06v0_nvt, 7.3 × 21.38, nf=1; single device in addressed array |
| 401 | ISOFETs!B3 | ISOFet1/R2 | sky130_fd_pr__nfet_01v8 | W=0.36 L=1 | 1=B2 2=S2 3=G2 4=X2 5=D2 | nfet_03v3, 0.42 × 1.13, nf=1; contacted LVPWELL in separate DNWELL; independent body, DNWELL pickup and VSS guard |
| 402 | ISOFETs!B3 | ISOFet1/R3 | sky130_fd_pr__nfet_01v8 | W=1 L=1 | 6=B3 7=S3 8=G3 9=X3 10=D3 | nfet_03v3, 1 × 1.13, nf=1; contacted LVPWELL in separate DNWELL; independent body, DNWELL pickup and VSS guard |
| 403 | ISOFETs!B11 | ISOFet1/R1 | sky130_fd_pr__nfet_01v8 | W=0.36 L=0.15 | 1=B1 2=S1 3=G1 4=X1 5=D1 | nfet_03v3, 0.42 × 0.28, nf=1; contacted LVPWELL in separate DNWELL; independent body, DNWELL pickup and VSS guard |
| 404 | ISOFETs!B11 | ISOFet1/R4 | sky130_fd_pr__nfet_01v8 | W=1 L=0.15 | 6=B4 7=S4 8=G4 9=X4 10=D4 | nfet_03v3, 1 × 0.28, nf=1; contacted LVPWELL in separate DNWELL; independent body, DNWELL pickup and VSS guard |
| 405 | ISOFETs!B21 | ISOFet2/R2 | sky130_fd_pr__pfet_01v8 | W=0.42 L=1 | 1=B2 2=S2 3=G2 4=X2 5=D2 | pfet_03v3, 0.42 × 1.13, nf=1; independent four-terminal cell |
| 406 | ISOFETs!B21 | ISOFet2/R3 | sky130_fd_pr__pfet_01v8 | W=1 L=1 | 6=B3 7=S3 8=G3 9=X3 10=D3 | pfet_03v3, 1 × 1.13, nf=1; independent four-terminal cell |
| 407 | ISOFETs!B29 | ISOFet2/R1 | sky130_fd_pr__pfet_01v8 | W=0.42 L=0.15 | 1=B1 2=S1 3=G1 4=X1 5=D1 | pfet_03v3, 0.42 × 0.28, nf=1; independent four-terminal cell |
| 408 | ISOFETs!B29 | ISOFet2/R4 | sky130_fd_pr__pfet_01v8 | W=1 L=0.15 | 6=B4 7=S4 8=G4 9=X4 10=D4 | pfet_03v3, 1 × 0.28, nf=1; independent four-terminal cell |
| 409 | ISOFETs!B39 | ISOFet3/R2 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5 L=1 | 1=B2 2=S2 3=G2 4=X2 5=D2 | nfet_06v0, 0.5 × 1.28, nf=1; contacted LVPWELL in separate DNWELL; independent body, DNWELL pickup and VSS guard |
| 410 | ISOFETs!B39 | ISOFet3/R3 | sky130_fd_pr__nfet_g5v0d10v5 | W=1 L=1 | 6=B3 7=S3 8=G3 9=X3 10=D3 | nfet_06v0, 1 × 1.28, nf=1; contacted LVPWELL in separate DNWELL; independent body, DNWELL pickup and VSS guard |
| 411 | ISOFETs!B47 | ISOFet3/R1 | sky130_fd_pr__nfet_g5v0d10v5 | W=0.5 L=0.42 | 1=B1 2=S1 3=G1 4=X1 5=D1 | nfet_06v0, 0.5 × 0.7, nf=1; contacted LVPWELL in separate DNWELL; independent body, DNWELL pickup and VSS guard |
| 412 | ISOFETs!B47 | ISOFet3/R4 | sky130_fd_pr__nfet_g5v0d10v5 | W=1 L=0.42 | 6=B4 7=S4 8=G4 9=X4 10=D4 | nfet_06v0, 1 × 0.7, nf=1; contacted LVPWELL in separate DNWELL; independent body, DNWELL pickup and VSS guard |
| 413 | ISOFETs!B57 | ISOFet4/R2 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5 L=1 | 1=B2 2=S2 3=G2 4=X2 5=D2 | pfet_06v0, 0.5 × 1.13, nf=1; independent four-terminal cell |
| 414 | ISOFETs!B57 | ISOFet4/R3 | sky130_fd_pr__pfet_g5v0d10v5 | W=1 L=1 | 6=B3 7=S3 8=G3 9=X3 10=D3 | pfet_06v0, 1 × 1.13, nf=1; independent four-terminal cell |
| 415 | ISOFETs!B65 | ISOFet4/R1 | sky130_fd_pr__pfet_g5v0d10v5 | W=0.5 L=0.42 | 1=B1 2=S1 3=G1 4=X1 5=D1 | pfet_06v0, 0.5 × 0.55, nf=1; independent four-terminal cell |
| 416 | ISOFETs!B65 | ISOFet4/R4 | sky130_fd_pr__pfet_g5v0d10v5 | W=1 L=0.42 | 6=B4 7=S4 8=G4 9=X4 10=D4 | pfet_06v0, 1 × 0.55, nf=1; independent four-terminal cell |
| 417 | MOSCAPs!B3 | MOSCAP1 | sky130_fd_pr__nfet_01v8 | MOSCAP Module W=40, L=40 | 1=G 2=SDB | nfet_03v3, five parallel 40 × 40 plates; nf=1 per plate; S/D/B strapped at cell |
| 418 | MOSCAPs!B13 | MOSCAP2 | sky130_fd_pr__npfet_01v8 | MOSCAP Module W=40, L=40 | 1=G 2=SDB | pfet_03v3, five parallel 40 × 40 plates; nf=1 per plate; S/D/B strapped at cell |
| 419 | MOSCAPs!B23 | MOSCAP3 | sky130_fd_pr__nfet_01v8_lvt | MOSCAP Module W=40, L=40 | 1=G 2=SDB | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 420 | MOSCAPs!B33 | MOSCAP4 | sky130_fd_pr__pfet_01v8_lvt | MOSCAP Module W=40, L=40 | 1=G 2=SDB | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 421 | MOSCAPs!B43 | MOSCAP5 | sky130_fd_pr__nfet_g5v0d10v5 | MOSCAP Module W=40, L=40 | 1=G 2=SDB | nfet_06v0, five parallel 40 × 40 plates; nf=1 per plate; S/D/B strapped at cell |
| 422 | MOSCAPs!B53 | MOSCAP6 | sky130_fd_pr__pfet_g5v0d10v5 | MOSCAP Module W=40, L=40 | 1=G 2=SD | pfet_06v0, five parallel 40 × 40 plates; nf=1 per plate; SD brought out, separate body bias |
| 423 | MOSCAPs!B63 | MOSCAP7 | sky130_fd_pr__nfet_03v3_nvt | MOSCAP Module W=40, L=40 | 1=G 2=SDB | nfet_06v0_nvt, five parallel 40 × 40 plates; nf=1 per plate; S/D/B strapped at cell |
| 424 | MOSCAPOVLs!B3 | MOSCAPOVL1/R3 | sky130_fd_pr__nfet_01v8 | Overlap Module 3, W=0.36, L=0.25, Lcomb=Long | 1=G 2=SD 3=B | nfet_03v3, 0.36 × 0.38 per finger, 10 parallel; 30 µm comb, separate body |
| 425 | MOSCAPOVLs!B11 | MOSCAPOVL1/R2 | sky130_fd_pr__nfet_01v8 | Overlap Module 2, W=Long, L=0.25 | 1=G 2=SD 3=B | nfet_03v3, 30 × 0.38 per finger, 10 parallel; overlap stripe, separate body |
| 426 | MOSCAPOVLs!B19 | MOSCAPOVL1/R1 | sky130_fd_pr__nfet_01v8 | Overlap Module 1, W=Long, L=0.15 | 1=G 2=SD 3=B | nfet_03v3, 30 × 0.28 per finger, 10 parallel; overlap stripe, separate body |
| 427 | MOSCAPOVLs!B29 | MOSCAPOVL2/R3 | sky130_fd_pr__npfet_01v8 | Overlap Module 3, W=0.42, L=0.25, Lcomb=Long | 1=G 2=SD 3=B | pfet_03v3, 0.42 × 0.38 per finger, 10 parallel; 30 µm comb, separate body |
| 428 | MOSCAPOVLs!B37 | MOSCAPOVL2/R2 | sky130_fd_pr__npfet_01v8 | Overlap Module 2, W=Long, L=0.25 | 1=G 2=SD 3=B | pfet_03v3, 30 × 0.38 per finger, 10 parallel; overlap stripe, separate body |
| 429 | MOSCAPOVLs!B45 | MOSCAPOVL2/R1 | sky130_fd_pr__npfet_01v8 | Overlap Module 1, W=Long, L=0.15 | 1=G 2=SD 3=B | pfet_03v3, 30 × 0.28 per finger, 10 parallel; overlap stripe, separate body |
| 430 | MOSCAPOVLs!B55 | MOSCAPOVL3/R3 | sky130_fd_pr__nfet_01v8_lvt | Overlap Module 3, W=0.42, L=0.25, Lcomb=Long | 1=G 2=SD 3=B | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 431 | MOSCAPOVLs!B63 | MOSCAPOVL3/R2 | sky130_fd_pr__nfet_01v8_lvt | Overlap Module 2, W=Long, L=0.25 | 1=G 2=SD 3=B | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 432 | MOSCAPOVLs!B71 | MOSCAPOVL3/R1 | sky130_fd_pr__nfet_01v8_lvt | Overlap Module 1, W=Long, L=0.15 | 1=G 2=SD 3=B | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 433 | MOSCAPOVLs!B81 | MOSCAPOVL4/R3 | sky130_fd_pr__pfet_01v8_lvt | Overlap Module 3, W=0.42, L=0.5, Lcomb=Long | 1=G 2=SD 3=B | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 434 | MOSCAPOVLs!B89 | MOSCAPOVL4/R2 | sky130_fd_pr__pfet_01v8_lvt | Overlap Module 2, W=Long, L=0.5 | 1=G 2=SD 3=B | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 435 | MOSCAPOVLs!B97 | MOSCAPOVL4/R1 | sky130_fd_pr__pfet_01v8_lvt | Overlap Module 1, W=Long, L=0.35 | 1=G 2=SD 3=B | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 436 | MOSCAPOVLs!B107 | MOSCAPOVL5/R3 | sky130_fd_pr__nfet_g5v0d10v5 | Overlap Module 3, W=0.42, L=0.8, Lcomb=Long | 1=G 2=SD 3=B | nfet_06v0, 0.42 × 1.08 per finger, 10 parallel; 30 µm comb, separate body |
| 437 | MOSCAPOVLs!B115 | MOSCAPOVL5/R2 | sky130_fd_pr__nfet_g5v0d10v5 | Overlap Module 2, W=Long, L=0.8 | 1=G 2=SD 3=B | nfet_06v0, 30 × 1.08 per finger, 10 parallel; overlap stripe, separate body |
| 438 | MOSCAPOVLs!B123 | MOSCAPOVL5/R1 | sky130_fd_pr__nfet_g5v0d10v5 | Overlap Module 1, W=Long, L=0.5 | 1=G 2=SD 3=B | nfet_06v0, 30 × 0.78 per finger, 10 parallel; overlap stripe, separate body |
| 439 | MOSCAPOVLs!B133 | MOSCAPOVL6/R3 | sky130_fd_pr__pfet_g5v0d10v5 | Overlap Module 3, W=0.42, L=0.8, Lcomb=Long | 1=G 2=SD 3=B | pfet_06v0, 0.42 × 0.93 per finger, 10 parallel; 30 µm comb, separate body |
| 440 | MOSCAPOVLs!B141 | MOSCAPOVL6/R2 | sky130_fd_pr__pfet_g5v0d10v5 | Overlap Module 2, W=Long, L=0.8 | 1=G 2=SD 3=B | pfet_06v0, 30 × 0.93 per finger, 10 parallel; overlap stripe, separate body |
| 441 | MOSCAPOVLs!B149 | MOSCAPOVL6/R1 | sky130_fd_pr__pfet_g5v0d10v5 | Overlap Module 1, W=Long, L=0.5 | 1=G 2=SD 3=B | pfet_06v0, 30 × 0.63 per finger, 10 parallel; overlap stripe, separate body |
| 442 | MOSCAPOVLs!B159 | MOSCAPOVL7/R3 | sky130_fd_pr__nfet_03v3_nvt | Overlap Module 3, W=0.42, L=0.8, Lcomb=Long | 1=G 2=SD 3=B | nfet_06v0_nvt, 0.80 × 2.18 per finger, 10 parallel; 30 µm comb, separate body |
| 443 | MOSCAPOVLs!B167 | MOSCAPOVL7/R2 | sky130_fd_pr__nfet_03v3_nvt | Overlap Module 2, W=Long, L=0.8 | 1=G 2=SD 3=B | nfet_06v0_nvt, 30 × 2.18 per finger, 10 parallel; overlap stripe, separate body |
| 444 | MOSCAPOVLs!B175 | MOSCAPOVL7/R1 | sky130_fd_pr__nfet_03v3_nvt | Overlap Module 1, W=Long, L=0.5 | 1=G 2=SD 3=B | nfet_06v0_nvt, 30 × 1.88 per finger, 10 parallel; overlap stripe, separate body |
| 445 | AreaDiodes!B3 | AreaDiode1 | sky130_fd_pr__diode_pw2nd_05v5 | Diode Module W=40, L=40 | 1=C1 2=A1 | diode_nd2ps_06v0, five parallel 40 × 40 junctions, area array |
| 446 | AreaDiodes!B13 | AreaDiode2 | sky130_fd_pr__diode_pd2nw_05v5 | Diode Module W=40, L=40 | 1=C1 2=A1 | diode_pd2nw_06v0, five parallel 40 × 40 junctions, area array |
| 447 | AreaDiodes!B23 | AreaDiode3 | sky130_fd_pr__diode_pw2nd_05v5_lvt | Diode Module W=40, L=40 | 1=C1 2=A1 | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 448 | AreaDiodes!B33 | AreaDiode4 | sky130_fd_pr__diode_pd2nw_05v5_lvt | Diode Module W=40, L=40 | 1=C1 2=A1 | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 449 | AreaDiodes!B43 | AreaDiode5 | sky130_fd_pr__diode_pw2nd_05v5_nvt | Diode Module W=40, L=40 | 1=C1 2=A1 | Dropped — no matching threshold-implant option for this structure in GF180D. |
| 450 | AreaDiodes!B53 | AreaDiode6 | sky130_fd_pr__diode_pw2nd_05v5 | Diode Module W=40, L=40 | 1=C1 2=A1 | diode_nd2ps_06v0, five parallel 40 × 40 junctions, area array |
| 451 | AreaDiodes!B63 | AreaDiode7 | sky130_fd_pr__diode_pd2nw_05v5 | Diode Module W=40, L=40 | 1=C1 2=A1 | diode_pd2nw_06v0, five parallel 40 × 40 junctions, area array |
| 452 | AreaMIMC!B3 | AreaMIMC1 | sky130_fd_pr__model__cap_mim | Area MIMC Module W=40, L=40 | 1=C1 2=A1 | M4/top 2 fF/µm² MIM; five parallel 40 × 40 plates (separate instance) |
| 453 | AreaMIMC!B13 | AreaMIMC2 | sky130_fd_pr__cap_mim_m4 | Area MIMC Module W=40, L=40 | 1=C1 2=A1 | M4/top 2 fF/µm² MIM; five parallel 40 × 40 plates (separate instance) |
| 454 | PeriMIMC!B3 | PeriMIMC1 | sky130_fd_pr__model__cap_mim_m3 | Mimcap Perimeter Module, W=1, L=1, pitch-x=2.48,  pitch-y=2.48 | 1=C1 2=A1 11=C 12=A | M4/top 2 fF/µm² MIM; 20 parallel arrays, 5 × 5 units on 12.4 × 12.4 pitch; perimeter pattern |
| 455 | PeriMIMC!B13 | PeriMIMC2 | sky130_fd_pr__cap_mim_m4 | Mimcap Perimeter Module, W=2, L=2, pitch-x=4,  pitch-y=4 | 1=C1 2=A1 11=C 12=A | M4/top 2 fF/µm² MIM; 20 parallel arrays, 10 × 10 units on 20 × 20 pitch; perimeter pattern |
| 456 | PrRES!B3 | PRES1/R2 | sky130_fd_pr__res_high_po | W=0.35 L=20 | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | ppolyf_u, 0.8 × 20.45, one unsilicided stripe; four-terminal Kelvin |
| 457 | PrRES!B3 | PRES1/R3 | sky130_fd_pr__res_high_po | W=5.73 L=20 | 5=Sense T3 6=R3T 7=R3T 8=Sense B3 | ppolyf_u, 6.18 × 20.45, one unsilicided stripe; four-terminal Kelvin |
| 458 | PrRES!B11 | PRES1/R1 | sky130_fd_pr__res_high_po | W=0.35 L=0.35 | 1=Sense T1 2=R1T 3=R1B 4=Sense B1 | ppolyf_u, 0.8 × 0.8, one unsilicided stripe; four-terminal Kelvin |
| 459 | PrRES!B11 | PRES1/R4 | sky130_fd_pr__res_high_po | W=5.73 L=0.35 | 5=Sense T4 6=R4T 7=R4B 8=Sense B4 | ppolyf_u, 6.18 × 0.8, one unsilicided stripe; four-terminal Kelvin |
| 460 | PrRES!B21 | PRES2/R2 | sky130_fd_pr__res_xhigh_po | W=0.35 L=20 | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | ppolyf_u_1k, 1 × 20.65, one unsilicided stripe; four-terminal Kelvin |
| 461 | PrRES!B21 | PRES2/R3 | sky130_fd_pr__res_xhigh_po | W=5.73 L=20 | 5=Sense T3 6=R3T 7=R3T 8=Sense B3 | ppolyf_u_1k, 6.38 × 20.65, one unsilicided stripe; four-terminal Kelvin |
| 462 | PrRES!B29 | PRES2/R1 | sky130_fd_pr__res_xhigh_po | W=0.35 L=0.35 | 1=Sense T1 2=R1T 3=R1B 4=Sense B1 | ppolyf_u_1k, 1 × 1, one unsilicided stripe; four-terminal Kelvin |
| 463 | PrRES!B29 | PRES2/R4 | sky130_fd_pr__res_xhigh_po | W=5.73 L=0.35 | 5=Sense T4 6=R4T 7=R4B 8=Sense B4 | ppolyf_u_1k, 6.38 × 1, one unsilicided stripe; four-terminal Kelvin |
| 464 | ResMet!B3 | Restmet1 | LI | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Dropped — GF180D has no patterned SKY130 local-interconnect layer. |
| 465 | ResMet!B13 | Restmet2 | M2 | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Metal2, 40 µm end-to-end turns; minimum legal width/space, four-terminal serpentine |
| 466 | ResMet!B23 | Restmet3 | M3 | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Metal3, 40 µm end-to-end turns; minimum legal width/space, four-terminal serpentine |
| 467 | ResMet!B33 | Restmet4 | M4 | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Metal4, 40 µm end-to-end turns; minimum legal width/space, four-terminal serpentine |
| 468 | ResMet!B43 | Restmet5 | M5 | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | MetalTop, 40 µm end-to-end turns; minimum legal width/space, four-terminal serpentine |
| 469 | ResMet!B54 | Restmet6 | M6 | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Dropped — GF180D has five routing metals. |
| 470 | ResMet!B65 | Restmet7 | LI | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Dropped — GF180D has no patterned SKY130 local-interconnect layer. |
| 471 | ResMet!B75 | Restmet8 | M2 | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Metal2, 40 µm end-to-end turns; minimum legal width/space, four-terminal serpentine |
| 472 | ResMet!B85 | Restmet9 | M3 | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Metal3, 40 µm end-to-end turns; minimum legal width/space, four-terminal serpentine |
| 473 | ResMet!B95 | Restmet10 | M4 | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Metal4, 40 µm end-to-end turns; minimum legal width/space, four-terminal serpentine |
| 474 | ResMet!B105 | Restmet11 | M5 | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | MetalTop, 40 µm end-to-end turns; minimum legal width/space, four-terminal serpentine |
| 475 | ResMet!B116 | Restmet12 | M6 | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Dropped — GF180D has five routing metals. |
| 476 | ResMet!B127 | Restmet13 | LI | 40 micron turns end to end | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Dropped — GF180D has no patterned SKY130 local-interconnect layer. |
| 477 | VDaisy!B3 | VDAISY1 | LI-M1 | 40 micron turns end to end, minimum via length | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | Dropped — GF180D has no LI–M1 interconnect. |
| 478 | VDaisy!B13 | VDAISY2 | M1-M2 | 40 micron turns end to end, minimum via length | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | via1, 40 µm end-to-end turns; minimum legal via and spacing, four-terminal alternating-layer chain |
| 479 | VDaisy!B23 | VDAISY3 | M2-M3 | 40 micron turns end to end, minimum via length | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | via2, 40 µm end-to-end turns; minimum legal via and spacing, four-terminal alternating-layer chain |
| 480 | VDaisy!B33 | VDAISY4 | M3-M4 | 40 micron turns end to end, minimum via length | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | via3, 40 µm end-to-end turns; minimum legal via and spacing, four-terminal alternating-layer chain |
| 481 | VDaisy!B44 | VDAISY5 | M4-M5 | 40 micron turns end to end, minimum via length | 1=Sense T2 2=R2T 3=R2B 4=Sense B2 | via4, 40 µm end-to-end turns; minimum legal via and spacing, four-terminal alternating-layer chain |
| 482 | ROSC!B3,B11 | sky130hd inverter | sky130hd inverter | nfet: nfet_01v8, pfet: pfet_hvt_01v8 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | gf180mcu_fd_sc_mcu7t5v0__inv_1; RO pattern below; unit-cell W/L/fingers fixed by library |
| 483 | ROSC!B21,B29 | sky130hs inverter | sky130hs inverter | nfet: nfet_01v8_lvt, pfet: pfet_01v8 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | gf180mcu_fd_sc_mcu9t5v0__inv_1; RO pattern below; HS specimen; same inverter and supply as 484, separate placement |
| 484 | ROSC!B39,B47 | sky130hvl inverter | sky130hvl inverter | nfet: nfet_gv0d10v5, pfet: pfet_gv0d10v5 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | gf180mcu_fd_sc_mcu9t5v0__inv_1; RO pattern below; HVL specimen; same inverter and supply as 483, so the SKY HS/HVL process distinction is lost |
| 485 | ROSC!B57,B65 | sky130osu12Ths inverter | sky130osu12Ths inverter | nfet: nfet_01v8_lvt, pfet: pfet_01v8 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | Dropped — no GF180D library with this track height and speed/threshold class. |
| 486 | ROSC!B75,B83 | sky130osu12Tls inverter | sky130osu12Tls inverter | nfet: nfet_01v8, pfet: pfet_hvt_01v8 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | Dropped — no GF180D library with this track height and speed/threshold class. |
| 487 | ROSC!B93,B101 | sky130osu12Tms inverter | sky130osu12Tms inverter | nfet: nfet_01v8, pfet: pfet_01v8 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | gf180mcu_osu_sc_gp12t3v3__inv_1; RO pattern below; hard inverter from the pinned PDK; verify its GDS and timing views in the template integration flow before inclusion |
| 488 | ROSC!B111,B119 | sky130osu15Ths | sky130osu15Ths | nfet: nfet_01v8_lvt, pfet: pfet_01v8 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | Dropped — no GF180D library with this track height and speed/threshold class. |
| 489 | ROSC!B129,B137 | sky130osu15TIs | sky130osu15TIs | nfet: nfet_01v8, pfet: pfet_hvt_01v8 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | Dropped — no GF180D library with this track height and speed/threshold class. |
| 490 | ROSC!B147,B155 | sky130osu15Tms | sky130osu15Tms | nfet: nfet_01v8, pfet: pfet_01v8 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | Dropped — no GF180D library with this track height and speed/threshold class. |
| 491 | ROSC!B165,B173 | sky130osu18Ths | sky130osu18Ths | nfet: nfet_01v8_lvt, pfet: pfet_01v8 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | Dropped — no GF180D library with this track height and speed/threshold class. |
| 492 | ROSC!B183,B191 | sky130osu18TIs | sky130osu18TIs | nfet: nfet_01v8, pfet: pfet_hvt_01v8 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | Dropped — no GF180D library with this track height and speed/threshold class. |
| 493 | ROSC!B201,B209 | sky130osu18Tms | sky130osu18Tms | nfet: nfet_01v8, pfet: pfet_01v8 | R2 1=NC 2=VRO 3=VRO 4=NC; R1 1=X 2=EBL 3=GND 4=OUT | Dropped — no GF180D library with this track height and speed/threshold class. |
