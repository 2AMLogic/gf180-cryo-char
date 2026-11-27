# GF180D MIM characterization specimens

The two area specimens and two perimeter specimens implement selection codes 452–455 from the [characterization map](../../spec/structure-map.md). Each uses the GF180D option-B 2 fF/µm² M4/M5 stack. Codes 452 and 453 have distinct top cells for separate physical placements. Their geometries and expected capacitances are identical.

| Code | NIST structure | Unit count × square side | Plate area (µm²) | Plate perimeter (µm) | Filled width × height (µm) | Simulated min / typical / max (pF) |
|---|---|---:|---:|---:|---:|---:|
| 452 | AreaMIMC1 | 5 × 40 µm | 8,000 | 800 | 286.8 × 130 | 14.482 / 16.111 / 17.738 |
| 453 | AreaMIMC2 | 5 × 40 µm | 8,000 | 800 | 286.8 × 130 | 14.482 / 16.111 / 17.738 |
| 454 | PeriMIMC1 | 3,920 × 5 µm | 98,000 | 78,400 | 1,277.0 × 1,036.2 | 192.105 / 213.703 / 235.286 |
| 455 | PeriMIMC2 | 1,620 × 10 µm | 162,000 | 64,800 | 1,280.8 × 1,040.0 | 303.680 / 337.822 / 371.940 |

Each perimeter specimen places twenty 14 × 14 (166.2 × 166.2 µm) or 9 × 9 (170.0 × 170.0 µm) plate arrays—the spec's 175 µm windows with 4.4 µm or 2.5 µm edge clearance—on a 260 µm pitch. Standalone cell DRC enforces global density over the macro extent (`DCF.1b` ≥ 25% COMP, `PL.8` ≥ 14% Poly2, `M1.4`–`M5.4` and `MT.3` > 30% metal), while `DM.8` requires 6 µm from dummy metal to `FuseTop` (`75/0`, the option-B top plate) and the pinned `fill_partitions.py` applies that same 6 µm `FuseTop` halo to FEOL fill. Adjacent `FuseTop` plates inside each window sit 7.4 µm (code 454) and 10.0 µm (code 455) apart (< 12 µm), excluding all fill inside the 20 windows. At a bare 175 µm window pitch the inter-window `FuseTop` gaps are 8.8 µm and 5.0 µm (< 12 µm), excluding fill between windows as well and failing standalone density (`M3.4` 15.13% and 13.64%, `DCF.1b` 12.20% and 12.16%). With the 0.8 µm `Metal3` bottom-plate row buses (`DM.3` 2 µm halo), code 455 first clears `M3.4` > 30% at 249 µm pitch (30.02%); 260 µm provides ~2% `M3.4` margin (32.24% on 454, 32.33% on 455). Anchoring each grid at `(260 · ix, 260 · iy)` without an unmarked 175 µm frame is a uniform 4.4 / 2.5 µm translation absorbed by the outer bus margins, leaving every inter-plate and inter-window spacing unchanged. One Metal5 bus contacts the top plates. Each Metal4 bottom plate has its own Via3 contact to a common Metal3 bus. The gLayout unit omits its optional Metal5 bottom-plate extension because the bottom terminal already has a separate route. Each specimen has two electrically distinct terminals, top and bot. The four filled bounding boxes sum to 2.73 mm² before pad, mux and die routing. The tile floorplan must accommodate these macros and independently route their four readout leads.

[Verification results](verification.json) identify each delivered stream by SHA-256. The pinned native GF180D run covers 763 declared categories, and the curated run covers 25. Dimensional LVS anchors both terminals by name and compares each capacitor's plate area and perimeter individually. The negative control cuts the first Metal3 row outside the individual plate contacts. This produces a third extracted net and an LVS mismatch in every specimen.

The [108 AC results](measurements.csv), recorded in an append-only [`klt sim` batch envelope](records/20261127-043435-f6bf3eb-ac/sim.envelope.json) and [NIST-ID manifest](records/20261127-043435-f6bf3eb-ac/manifest.json), verify each stream's SHA-256 against `verification.json`, run a fresh GF180D device extraction for each stream, and submit one 27-corner × 4-specimen `klt sim` request (`--wait-for-capacity 600`) across three MIM model corners, −40/25/125 °C, and 0/1.65/3.3 V DC bias (`measure.py` invokes `klt sim` directly rather than `sim/harness/runner.py`'s local `ngspice -b` pool). Measurements are keyed by NIST structure ID (`AreaMIMC1`, `AreaMIMC2`, `PeriMIMC1`, `PeriMIMC2`). The stimulus is 10 mV at 10 kHz. The typical column uses the typical capacitor model at 25 °C and 1.65 V. The reported capacitance comes from the imaginary part of the AC source current. Wire RC, pad and instrument loading, guard switches, and cryogenic behavior remain outside this calculation. Measurements on the assembled tile require those contributions to be characterized separately.

## Four-wire access

For codes 452–455, the GF180 port assigns terminal 1 (`C1`, F1/S1) to the physical top plate and terminal 2 (`A1`, F2/S2) to the Metal4 bottom plate. The [source workbook mapping](../../spec/structure-map.md) and NIST module-description slides 15–18 identify C1/A1 but give no MIM plate cross-section tying those names to a metal level. This is the GF180 port's convention. The [AC bench](measure.py) applies its recorded bias as V(top) − V(bottom). The NIST MDM files name their swept voltage `vbc` across instrument terminals B and C. A signed cross-process C–V comparison requires a source-backed mapping of those terminals to physical electrodes.

The routing abstract places F1 and S1 on the Metal5 top-plate spine at the east edge and F2 and S2 on the Metal3 bottom-plate spine at the west edge. Force approaches at the south end of each spine and sense at the north. Each horizontal approach has a 0.8 × 4 µm landing. Route four separate leads from the selection switches. Each force/sense pair joins at its plate inside the macro. Readout still needs die routing, extracted interconnect and pad/fixture calibration. [OpenROAD LEF](mim_kelvin.lef)

Use the generated `mim_<code>_kelvin.gds` top with this LEF. Its lower-left outline is at (0, 0). A single translated instance preserves the source capacitor and fill geometry and the two original electrode labels. Metal1 through Metal5 and all intervening via layers are obstructed outside the specified metal access corridors. Each exported top passed the GF180D native and curated DRC runs (763 and 25 categories). [Wrapped-stream DRC](kelvin-drc.json)

OpenROAD reads the checked-in LEF using the GF180D technology file. The probe connects four separate traces to the parsed pin rectangles. KLayout checks the opposite ends of those traces against both electrodes of every physical capacitor. Cutting each of the 16 spines individually isolates its external trace. A separate inserted via-stack bridge shorts the two plates in each specimen. [Physical probe results](kelvin-access.json)

## Placement on the prechecked template

The template’s 114 rectangular Metal5 conductors span the full width of the snapped core. The largest clear vertical interval, including the two core edges, is 64 µm. OpenROAD reads a Metal5 routing obstruction at every horizontal slice of all four proposed macros. The same holds after a quarter turn. A complete macro therefore conflicts with the existing grid everywhere inside the core. The counts below use the full-width Metal5 conductors alone. Metal4, local supply rails, vias, standard cells and pads would impose further constraints. [Template build record](https://github.com/2AMLogic/gf180-cryo-char/blob/aca3e92a65428a1fe2f7a3189ee50a0271a6b9bc/layout/build/records/20261126-130323-f191663-template/record.json) · [Exact intervals and lower bounds](template-grid.json)

| Select code | Minimum Metal5 bands crossing the LEF obstruction | After a quarter turn |
|---|---:|---:|
| 452, 453 | 2 each | 6 each |
| 454 | 26 | 34 |
| 455 | 27 | 34 |

For the December 9 freeze, place the macros before generating the power grid. Route the supply grid outside their obstructions, then check supply continuity and current capacity, four-wire signal routing, and the populated die’s full precheck. The existing template’s passing precheck covers its recorded GDS.

Replay against the GDS and matching record from the [template checkout](https://github.com/2AMLogic/gf180-cryo-char/tree/aca3e92a65428a1fe2f7a3189ee50a0271a6b9bc). Set `template` to that checkout and use the same OpenROAD and PDK as the Kelvin check below.

```sh
record=20261126-130323-f191663-template
klt artifact get "$template/layout/artifacts.json#build/$record/chip_top.gds" -o /tmp/cryo-template.gds
uv run --script layout/mim/template_grid.py --die /tmp/cryo-template.gds \
    --build-record "$template/layout/build/records/$record/record.json" \
    --pdk "$PDK_ROOT/gf180mcuD" > /tmp/cryo-template-grid.json
cmp layout/mim/template-grid.json /tmp/cryo-template-grid.json
```

## Replay

Install the GF180D open_pdks revision and put native KLayout 0.30.14 and OpenROAD on PATH (`measure.py` submits its AC corner matrix to the `klt sim` batch fleet with `--wait-for-capacity 600`; pass `--backend local` with ngspice 47 only on an offline dedicated host). The routing abstract was checked with OpenROAD 26Q3-1510-g6cb3f2b704. Set PDK_ROOT to the directory containing gf180mcuD. The scripts pin the Python KLayout package, KLT and gLayout versions. The density fill generator is pinned by both commit and SHA-256. An offline copy can be supplied with the --fill-script option.

```sh
uv run --script layout/mim/build.py --output /tmp/cryo-mim-rebuild
for code in 452 453 454 455; do
    cmp "layout/mim/mim_$code.gds" "/tmp/cryo-mim-rebuild/mim_$code.gds" || exit 1
done
uv run --script layout/mim/verify.py --pdk "$PDK_ROOT/gf180mcuD"
uv run --script layout/mim/measure.py --pdk "$PDK_ROOT/gf180mcuD"
uv run --script layout/mim/kelvin.py --output /tmp/cryo-mim-kelvin
uv run --script layout/mim/verify_kelvin.py --pdk "$PDK_ROOT/gf180mcuD"
```

To repeat the wrapped-stream DRC, use the generated streams above and the exact native category inventory. Both reports must return zero violations for each stream.

```bash
cd /tmp/cryo-mim-kelvin
klt=(uvx --from klayout-tools==0.9.2 klt)
native=(--engine klayout --pdk gf180mcuD --pdk-root "$PDK_ROOT" --deck-var variant=D --deck-var decks=all --deck-var threads=1)
"${klt[@]}" drc "${native[@]}" --list-rule-categories > rules.txt
for code in 452 453 454 455; do
    top="mim_${code}_kelvin"
    "${klt[@]}" drc "$top.gds" --top "$top" "${native[@]}" --expect-rule-categories-file rules.txt --format json > "$code.native.json" || exit 1
    "${klt[@]}" drc "$top.gds" --top "$top" --deck gf180mcu --format json > "$code.curated.json" || exit 1
done
```
