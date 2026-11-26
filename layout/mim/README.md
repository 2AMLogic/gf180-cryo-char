# GF180D MIM characterization specimens

The two area specimens and two perimeter specimens implement selection codes 452–455 from the [characterization map](../../spec/structure-map.md). Each uses the GF180D option-B 2 fF/µm² M4/M5 stack. Codes 452 and 453 have distinct top cells for separate physical placements. Their geometries and expected capacitances are identical.

| Code | NIST structure | Unit count × square side | Plate area (µm²) | Plate perimeter (µm) | Filled width × height (µm) | Simulated min / typical / max (pF) |
|---|---|---:|---:|---:|---:|---:|
| 452 | AreaMIMC1 | 5 × 40 µm | 8,000 | 800 | 286.8 × 130 | 14.482 / 16.111 / 17.738 |
| 453 | AreaMIMC2 | 5 × 40 µm | 8,000 | 800 | 286.8 × 130 | 14.482 / 16.111 / 17.738 |
| 454 | PeriMIMC1 | 3,920 × 5 µm | 98,000 | 78,400 | 1,277.0 × 1,036.2 | 192.105 / 213.703 / 235.286 |
| 455 | PeriMIMC2 | 1,620 × 10 µm | 162,000 | 64,800 | 1,280.8 × 1,040.0 | 303.680 / 337.822 / 371.940 |

Each perimeter specimen contains twenty 175 µm windows on a 260 µm pitch. The 454 windows hold 14 × 14 units on a 12.4 µm pitch. The 455 windows hold 9 × 9 units on a 20 µm pitch. One Metal5 bus contacts the top plates. Each Metal4 bottom plate has its own Via3 contact to a common Metal3 bus. The gLayout unit omits its optional Metal5 bottom-plate extension because the bottom terminal already has a separate route. Each specimen has two electrically distinct terminals, top and bot. The four filled bounding boxes sum to 2.73 mm² before pad, mux and die routing. The tile floorplan still needs to accommodate these macros and any separately routed sense terminals.

[Verification results](verification.json) identify each delivered stream by SHA-256. The pinned native GF180D run covers 763 declared categories, and the curated run covers 25. Dimensional LVS anchors both terminals by name and compares each capacitor's plate area and perimeter individually. The negative control cuts the first Metal3 row outside the individual plate contacts. This produces a third extracted net and an LVS mismatch in every specimen.

The [108 AC results](measurements.csv) use a fresh GF180D device extraction for each stream, three MIM model corners, −40/25/125 °C, and 0/1.65/3.3 V DC bias. The stimulus is 10 mV at 10 kHz. The typical column uses the typical capacitor model at 25 °C and 1.65 V. The reported capacitance comes from the imaginary part of the AC source current. Wire RC, pad and instrument loading, guard switches, and cryogenic behavior remain outside this calculation. Measurements on the assembled tile require those contributions to be characterized separately.

## Replay

Install the GF180D open_pdks revision and put native KLayout 0.30.14 and ngspice 47 on PATH. Set PDK_ROOT to the directory containing gf180mcuD. The scripts pin the Python KLayout package, KLT and gLayout versions. The density fill generator is pinned by both commit and SHA-256. An offline copy can be supplied with the --fill-script option.

```sh
uv run --script layout/mim/build.py --output /tmp/cryo-mim-rebuild
for code in 452 453 454 455; do
    cmp "layout/mim/mim_$code.gds" "/tmp/cryo-mim-rebuild/mim_$code.gds" || exit 1
done
uv run --script layout/mim/verify.py --pdk "$PDK_ROOT/gf180mcuD"
uv run --script layout/mim/measure.py --pdk "$PDK_ROOT/gf180mcuD" --jobs 4
```
