# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14", "klayout-tools==0.9.2"]
# ///
"""Build the physically switched ring views and replay the GF180D evidence."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen

import klayout.db as db

HERE = Path(__file__).resolve().parent
RINGS = HERE.parent / "rings"
sys.path.insert(0, str(RINGS))
from generate import FILL_SOURCE, FILL_SHA256, LIBRARIES  # noqa: E402
from verify import KLT, native_options, run  # noqa: E402

PINS = ["en", "rx", "read", "read_b", "vro", "vss"]
MOS = dict(
    w_um=0.42,
    l_um=0.28,
    fingers=1,
    rows=1,
    cols=1,
    dummy=0,
    topology="array",
    flavor="nfet",
    voltage_flavor="",
    gate_contact=True,
    add_guard_ring=True,
)
METALS = (34, 36, 42)
VIAS = (35, 38)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stream_options():
    options = db.SaveLayoutOptions()
    options.dbu = 0.001
    options.gds2_write_timestamps = False
    return options


def route(layout, cell, layer, start, end, width):
    x1, y1 = start
    x2, y2 = end
    if x1 != x2 and y1 != y2:
        raise ValueError("A Manhattan route must share an axis")
    d = width // 2
    cell.shapes(layout.layer(layer, 0)).insert(
        db.Box(min(x1, x2) - d, min(y1, y2) - d, max(x1, x2) + d, max(y1, y2) + d)
    )


def make_switch(pdk, scratch):
    leaf_file = scratch / "n.gds"
    report = run(
        [
            "gen",
            "mos_array",
            "--pdk",
            "gf180mcuD",
            "--pdk-root",
            pdk.parent,
            "--params",
            json.dumps(MOS),
            "--cell-name",
            "sw_n",
            "-o",
            leaf_file,
        ]
    )
    # The generator emits a 0.5 nm stream. Export on the native 1 nm grid
    # before copying cells between layouts. All conductor edges are on 5 nm.
    scaled = scratch / "n-1nm.gds"
    original = db.Layout()
    original.read(str(leaf_file))
    original.write(str(scaled), stream_options())
    layout = db.Layout()
    layout.read(str(scaled))
    if layout.dbu != 0.001:
        raise ValueError("Unexpected device stream grid")
    fet = layout.top_cell()
    ports = {
        p["name"]: (round(p["x_um"] * 1000), round(p["y_um"] * 1000))
        for p in report["ports"]
    }
    expected = {
        "U0_S": (210, 210),
        "U0_D": (1070, 210),
        "U0_G": (640, 1380),
        "TAP_S": (640, -860),
    }
    if any(ports.get(key) != point for key, point in expected.items()):
        raise ValueError("The device access coordinates changed")
    cell = layout.create_cell("cryo_read_switch")
    for x in (0, 5800):
        cell.insert(db.CellInstArray(fet.cell_index(), db.Trans(x, 0)))
    # Drain of pass device to source of clamp. Both substrate rings and
    # the clamp drain share a separate return below the two devices.
    for x, y in ((1070, 210), (6010, 210), (640, -860), (6440, -860), (6870, 210)):
        route(layout, cell, 35, (x, y), (x, y), 260)
        route(layout, cell, 36, (x, y), (x, y), 400)
    route(layout, cell, 36, (1070, 210), (6010, 210), 400)
    route(layout, cell, 36, (640, -860), (6870, -860), 400)
    route(layout, cell, 36, (6870, -860), (6870, 210), 400)
    return layout


def assemble(family, switch, fill, scratch):
    name = "ro_" + family
    layout = db.Layout()
    layout.read(str(RINGS / (name + ".gds")))
    top = layout.top_cell()
    assembly = name + "_read"
    top.name = assembly
    layout.delete_cell(layout.cell(name + "__density_fill").cell_index())
    leaf = layout.create_cell("cryo_read_switch")
    leaf.copy_tree(switch.top_cell())
    record = json.loads((RINGS / "verification.json").read_text())[family]
    out = record["port_centres"]["out"]
    px, py = out["x_nm"], out["y_nm"]
    xf, yf = -5750, py - 210
    top.insert(db.CellInstArray(leaf.cell_index(), db.Trans(db.Trans.M90, xf, yf)))
    input_pin = (xf - 210, py)
    for metal in METALS:
        route(layout, top, metal, input_pin, input_pin, 440)
    for via in VIAS:
        route(layout, top, via, input_pin, input_pin, 260)
    route(layout, top, 42, input_pin, (px, py), 340)
    route(layout, top, 36, (xf - 6440, yf - 860), (-3600, yf - 860), 400)
    for metal, x, y, label in (
        (36, xf - 1070, yf + 210, "rx"),
        (34, xf - 640, yf + 1380, "read"),
        (34, xf - 6440, yf + 1380, "read_b"),
    ):
        top.shapes(layout.layer(metal, 10)).insert(db.Text(label, db.Trans(x, y)))
    unfilled = scratch / (assembly + ".unfilled.gds")
    filled = scratch / (assembly + ".filled.gds")
    layout.write(str(unfilled), stream_options())
    subprocess.run(
        [
            sys.executable,
            fill,
            "--input",
            unfilled,
            "--output",
            filled,
            "--top",
            assembly,
            "--report",
            scratch / (assembly + ".fill.json"),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    # Each filled family can coexist with the other families in a die assembly.
    layout = db.Layout()
    layout.read(str(filled))
    layout.cell("density_fill").name = assembly + "__density_fill"
    dest = scratch / (assembly + ".gds")
    layout.write(str(dest), stream_options())
    ref = scratch / (assembly + ".spice")
    ref.write_text(
        (RINGS / (name + ".spice")).read_text()
        + f"\n.subckt {assembly} {' '.join(PINS)}\n"
        + f"Xcore en rawout vro vss {name}\n"
        + "Xpass rx read rawout vss nfet_03v3 L=0.28u W=0.42u\n"
        + "Xbleed vss read_b rx vss nfet_03v3 L=0.28u W=0.42u\n.ends\n"
    )
    return dest, ref, (input_pin, (px, py))


def verify(family, gds, ref, endpoints, pdk, categories, scratch):
    name = gds.stem
    req = {
        "layout": {
            "file": str(gds),
            "deck": "gf180mcu",
            "top": name,
            "declared_pins": PINS,
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
            "compare_parameters": {"nfet": ["L", "W"], "pfet": ["L", "W"]},
        },
    }
    if family != "12t":
        req["reference"]["device_map"] = {"nfet_05v0": "nfet", "pfet_05v0": "pfet"}
    lvs = run(["lvs", "-"], request=req)
    if lvs["status"] != "match" or any(
        set(lvs["counts"][k].values()) != {n}
        for k, n in (("devices", 294), ("nets", 152), ("pins", 6))
    ):
        raise ValueError(f"Incomplete transistor match for {name}")
    matched_pins = {
        (net["layout"].casefold(), net["reference"].casefold())
        for net in lvs["net_correspondence"]
        if net["pin"]
    }
    if matched_pins != {(pin, pin) for pin in PINS}:
        raise ValueError(
            f"Unexpected boundary correspondence for {name}: {matched_pins}"
        )
    # Cut only the midpoint of the new Metal3 run. Both devices remain drawn.
    (x1, y), (x2, _) = endpoints
    midpoint = (x1 + x2) // 2
    bad = db.Layout()
    bad.read(str(gds))
    shapes = bad.top_cell().shapes(bad.layer(42, 0))
    cut = db.Region(db.Box(midpoint - 400, y - 300, midpoint + 400, y + 300))
    remainder = db.Region(shapes) - cut
    shapes.clear()
    shapes.insert(remainder)
    broken = scratch / (name + ".open.gds")
    bad.write(str(broken), stream_options())
    req["layout"]["file"] = str(broken)
    opened = run(["lvs", "-"], request=req, codes=(3,))
    if opened["status"] != "mismatch" or opened["counts"]["nets"]["layout"] != 153:
        raise ValueError("The receiver contact open escaped LVS")
    pex = scratch / (name + ".pex.spice")
    ext = run(
        [
            "extract",
            gds,
            "--top",
            name,
            "--deck",
            "gf180mcu",
            "--pdk",
            "gf180mcuD",
            "--pdk-root",
            pdk.parent,
            "--deck-option",
            "metal_top=11K",
            "--pins",
            ",".join(PINS),
            "--parasitics",
            "-o",
            pex,
        ]
    )
    bodies = Counter((d["class"], d["nets"]["b"]) for d in ext["devices"])
    if bodies != {("nfet", "vss"): 148, ("pfet", "vro"): 146}:
        raise ValueError(f"Unexpected device bodies in {family}: {bodies}")
    native = run(
        [
            "drc",
            gds,
            "--top",
            name,
            "--deck",
            "gf180mcu",
            *native_options(pdk),
            "--expect-rule-categories-file",
            categories,
        ]
    )
    checked = set(native["coverage"]["rules_checked"])
    if (
        native["violation_count"]
        or checked != set(categories.read_text().splitlines())
        or len(checked) != 763
    ):
        raise ValueError("Native DRC did not check the full stream cleanly")
    curated = run(
        ["drc", gds, "--top", name, "--deck", "gf180mcu"],
        codes=(3,) if family == "12t" else (0,),
    )
    baseline = json.loads((RINGS / "verification.json").read_text())[family]
    if curated["rule_counts"] != baseline["curated"]["rules"]:
        raise ValueError("The integration added curated DRC findings")
    return {
        "gds_sha256": digest(gds),
        "schematic_sha256": digest(ref),
        "pex_sha256": digest(pex),
        "bare_ring_gds_sha256": baseline["gds_sha256"],
        "route_length_um": (x2 - x1) / 1000,
        "lvs": lvs["counts"],
        "feedback_to_receiver_open": opened["counts"],
        "body_connections": {"nfet_vss": 148, "pfet_vro": 146},
        "native": {
            "violations": 0,
            "checked_categories": len(checked),
            "deck": native["provenance"]["deck"],
        },
        "curated": curated["rule_counts"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", required=True, type=Path)
    parser.add_argument(
        "--fill-script",
        type=Path,
        help="local copy of the pinned GF180D fill generator",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="replace the physical views and verification record",
    )
    args = parser.parse_args()
    pdk = args.pdk.resolve()
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        fill = scratch / "fill_partitions.py"
        if args.fill_script:
            code = args.fill_script.read_bytes()
        else:
            with urlopen(FILL_SOURCE, timeout=30) as response:
                code = response.read()
        if hashlib.sha256(code).hexdigest() != FILL_SHA256:
            raise ValueError("Unexpected fill generator")
        fill.write_bytes(code)
        switch = make_switch(pdk, scratch)
        cats = scratch / "categories.txt"
        cats.write_text(
            subprocess.check_output(
                [
                    KLT,
                    "drc",
                    "--deck",
                    "gf180mcu",
                    *native_options(pdk),
                    "--list-rule-categories",
                ],
                text=True,
            )
        )
        summary = {}
        outputs = []
        for family in LIBRARIES:
            gds, ref, ends = assemble(family, switch, fill, scratch)
            summary[family] = verify(family, gds, ref, ends, pdk, cats, scratch)
            outputs.extend([gds, ref, gds.with_suffix(".pex.spice")])
        report = scratch / "verification.json"
        report.write_text(json.dumps(summary, indent=2) + "\n")
        for generated in [*outputs, report]:
            published = HERE / generated.name
            if args.record:
                published.write_bytes(generated.read_bytes())
            elif generated.read_bytes() != published.read_bytes():
                raise ValueError(f"Regeneration differs for {generated.name}")
    print(
        "Verified the three integrated rings, output opens, PEX and native and curated DRC."
    )


if __name__ == "__main__":
    main()
