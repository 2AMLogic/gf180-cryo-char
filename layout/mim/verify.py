# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14", "klayout-tools==0.9.2"]
# ///
"""Replay native DRC, dimensional LVS and disconnected row controls for MIM specimens."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import klayout.db as db
from build import CODES, HERE, dimensions, options

sys.path.insert(0, str(HERE.parent))
from toolchain_pin import check as check_toolchain

KLT = Path(sys.executable).with_name("klt")
MODEL = "cap_mim_2f0_m4m5_noshield"


def run(args, request=None, expected=0):
    result = subprocess.run(
        [KLT, *args, "--format", "json"],
        input=json.dumps(request) if request else None,
        text=True,
        capture_output=True,
    )
    if result.returncode != expected:
        raise ValueError(
            f"KLT exited {result.returncode}: {result.stdout[-1000:]} {result.stderr[-450:]}"
        )
    return json.loads(result.stdout)


def lvs_request(gds, name, ref):
    return {
        "layout": {
            "file": str(gds),
            "deck": "gf180mcu",
            "top": name,
            "declared_pins": ["top", "bot"],
            "deck_options": {"metal_top": "11K"},
        },
        "reference": {
            "netlist": str(ref),
            "top": name,
            "form": "subckt-call",
            "deck": "gf180mcu",
        },
        "options": {
            "flatten_layout": True,
            "flatten_reference": True,
            "combine_devices": False,
            "anchor_top_level_pins": True,
            "compare_parameters": {MODEL: ["A", "P"]},
        },
    }


def verify(code, native_args, categories, tmp):
    name = f"mim_{code}"
    gds = HERE / (name + ".gds")
    side, _, nx, ny, across, down = dimensions(code)
    count = nx * ny * across * down
    ref = tmp / (name + ".spice")
    cards = [
        f"Xc{i} bot top {MODEL} c_length={side}u c_width={side}u" for i in range(count)
    ]
    ref.write_text("\n".join([f".subckt {name} top bot", *cards, ".ends", ""]))
    request = lvs_request(gds, name, ref)
    good = run(["lvs", "-"], request)
    pins = {
        (net["layout"].lower(), net["reference"].lower())
        for net in good["net_correspondence"]
        if net["pin"]
    }
    coverage = good["device_parameter_coverage"]
    if (
        good["status"] != "match"
        or pins != {("top", "top"), ("bot", "bot")}
        or any(
            set(good["counts"][k].values()) != {v}
            for k, v in (("nets", 2), ("devices", count), ("pins", 2))
        )
        or len(coverage) != 1
        or coverage[0]["class"] != MODEL
        or set(coverage[0]["compared"]) != {"A", "P"}
    ):
        raise ValueError(f"Incomplete two-terminal physical match for {name}")

    # Break the first row's Metal3 connection outside its individual plate
    # landings. All unit capacitors and both terminal labels remain in the GDS.
    layout = db.Layout()
    layout.read(str(gds))
    cell = layout.top_cell()
    metal = cell.shapes(layout.layer(42, 0))
    x = round((-side / 2 - 31) / layout.dbu)
    cut = db.Box(x - 600, -600, x + 600, 600)
    remaining = db.Region(metal) - db.Region(cut)
    metal.clear()
    metal.insert(remaining)
    broken = tmp / (name + ".open.gds")
    layout.write(str(broken), options())
    request["layout"]["file"] = str(broken)
    opened = run(["lvs", "-"], request, expected=3)
    if opened["status"] != "mismatch" or opened["counts"]["nets"]["layout"] != 3:
        raise ValueError(f"Row open escaped the comparison on {name}")

    native = run(
        [
            "drc",
            gds,
            "--top",
            name,
            *native_args,
            "--expect-rule-categories-file",
            categories,
        ]
    )
    if (
        native["status"] != "clean"
        or native["violation_count"]
        or not native["coverage"]["known"]
        or set(native["coverage"]["checked"])
        != set(categories.read_text().splitlines())
    ):
        raise ValueError(f"Incomplete native DRC coverage for {name}")
    curated = run(["drc", gds, "--top", name, "--deck", "gf180mcu"])
    if curated["status"] != "clean" or curated["violation_count"] or not curated["coverage"]["known"]:
        raise ValueError(f"Curated DRC is incomplete or has findings for {name}")
    # The geometry grader checks A/P, while SPICE uses the PDK capacitor model.
    return {
        "sha256": hashlib.sha256(gds.read_bytes()).hexdigest(),
        "width_um": round(cell.dbbox().width(), 3),
        "height_um": round(cell.dbbox().height(), 3),
        "unit_side_um": side,
        "units": count,
        "total_plate_area_um2": count * side**2,
        "total_plate_perimeter_um": 4 * count * side,
        "lvs": good["counts"],
        "compared": coverage[0]["compared"],
        "open_lvs": opened["counts"],
        "curated_categories": len(curated["coverage"]["checked"]),
        "curated_violations": curated["violation_count"],
        "drc_categories": len(native["coverage"]["checked"]),
        "drc_violations": native["violation_count"],
        "drc_deck": native["provenance"]["deck"]["content_hash"],
        "drc_deck_tree": native["provenance"]["deck"]["tree"]["content_hash"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    pdk = args.pdk.absolute()
    check_toolchain(KLT, pdk)
    native_args = [
        "--engine",
        "klayout",
        "--pdk",
        "gf180mcuD",
        "--pdk-root",
        pdk.parent,
        "--deck-var",
        "variant=D",
        "--deck-var",
        "decks=all",
        "--deck-var",
        "threads=1",
    ]
    with tempfile.TemporaryDirectory() as temp:
        tmp = Path(temp)
        categories = tmp / "rules.txt"
        rules = subprocess.check_output(
            [KLT, "drc", *native_args, "--list-rule-categories"], text=True
        )
        if len(set(rules.splitlines())) != 763:
            raise ValueError("Native GF180D inventory changed")
        categories.write_text(rules)
        result = {
            str(code): verify(code, native_args, categories, tmp) for code in CODES
        }
    target = HERE / "verification.json"
    if args.record:
        target.write_text(json.dumps(result, indent=2) + "\n")
    elif json.loads(target.read_text()) != result:
        raise ValueError("Geometry, LVS or DRC evidence changed")
    print(
        "Four specimens matched, including complete 763-category DRC and four row-open controls."
    )


if __name__ == "__main__":
    main()
