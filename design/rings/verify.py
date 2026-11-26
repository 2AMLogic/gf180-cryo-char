# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14", "klayout-tools==0.9.2"]
# ///
"""Replay transistor LVS, physical feedback faults, extraction, and both DRC decks."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import klayout.db as db
from generate import HERE, LIBRARIES, PUBLIC, inputs

KLT = Path(sys.executable).with_name("klt")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, *, request=None, codes=(0,)):
    proc = subprocess.run(
        [KLT, *args, "--format", "json"],
        cwd=HERE,
        input=json.dumps(request) if request else None,
        capture_output=True,
        text=True,
    )
    if proc.returncode not in codes:
        raise RuntimeError(f"{args}: {proc.stdout[-900:]} {proc.stderr[-900:]}")
    return json.loads(proc.stdout)


def lvs(family, gds, fault=False):
    name = "ro_" + family
    req = {
        "layout": {
            "file": str(gds),
            "deck": "gf180mcu",
            "top": name,
            "deck_options": {"metal_top": "11K"},
            "declared_pins": PUBLIC,
        },
        "reference": {
            "netlist": str(HERE / (name + ".spice")),
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
        "portable_paths": True,
    }
    if family != "12t":
        # The 5 V library wrappers use the 6 V MOS model cards. The layout
        # deck recognizes their physical N/P classes and compares each W/L.
        req["reference"]["device_map"] = {"nfet_05v0": "nfet", "pfet_05v0": "pfet"}
    report = run(["lvs", "-"], request=req, codes=(3,) if fault else (0,))
    counts = report["counts"]
    if fault:
        if report["status"] != "mismatch" or (
            counts["nets"]["layout"],
            counts["nets"]["reference"],
        ) != (150, 149):
            raise ValueError(f"{name}: feedback open escaped LVS: {counts}")
    else:
        for key, expected in (("nets", 149), ("devices", 292), ("pins", 4)):
            if set(counts[key].values()) != {expected}:
                raise ValueError(f"{name}: incomplete transistor LVS: {counts}")
        pairs = {
            (n["layout"].casefold(), n["reference"].casefold())
            for n in report["net_correspondence"]
            if n["pin"]
        }
        if report["status"] != "match" or pairs != {(n, n) for n in PUBLIC}:
            raise ValueError(f"{name}: public pin correspondence differs: {pairs}")
    return counts


def cut_feedback(gds, dest):
    layout = db.Layout()
    layout.read(str(gds))
    shapes = layout.top_cell().shapes(layout.layer(46, 0))
    vertical = max(
        (s.bbox() for s in shapes.each() if s.is_box()), key=lambda box: box.height()
    )
    if vertical.width() != 400 or vertical.height() <= 30000:
        raise ValueError("The long Metal4 feedback track is missing")
    center = vertical.center()
    gap = db.Region(
        db.Box(center.x - 500, center.y - 500, center.x + 500, center.y + 500)
    )
    remainder = db.Region(shapes) - gap
    shapes.clear()
    shapes.insert(remainder)
    layout.write(str(dest))


def native_options(pdk):
    return [
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


def library_curated_control(pdk):
    library = LIBRARIES["12t"]
    source = inputs(pdk, "12t")["gds"]
    counts = Counter()
    for name, qty in (("inv_1", 142), ("nand2_1", 1), ("buf_1", 1)):
        r = run(
            ["drc", source, "--deck", "gf180mcu", "--top", library + "__" + name],
            codes=(3,),
        )
        for rule in ("nplus.enclosing.comp.1", "pplus.space.ncomp.1"):
            counts[rule] += qty * r["rule_counts"][rule]
    return dict(counts)


def check(family, pdk, categories, scratch, library_control):
    name = "ro_" + family
    stem = HERE / name
    gds = stem.with_suffix(".gds")
    counts = lvs(family, gds)
    opened = scratch / (name + "-open.gds")
    cut_feedback(gds, opened)
    open_counts = lvs(family, opened, fault=True)
    pex = scratch / (name + ".spice")
    ext = run(
        [
            "extract",
            gds,
            "--deck",
            "gf180mcu",
            "--top",
            name,
            "--pdk",
            "gf180mcuD",
            "--pdk-root",
            pdk.parent,
            "--deck-option",
            "metal_top=11K",
            "--pins",
            ",".join(PUBLIC),
            "--parasitics",
            "-o",
            pex,
        ]
    )
    if pex.read_bytes() != stem.with_suffix(".pex.spice").read_bytes():
        raise ValueError(f"{name}: the simulated netlist differs from fresh extraction")
    bodies = Counter((d["class"], d["nets"]["b"]) for d in ext["devices"])
    if bodies != {("nfet", "vss"): 146, ("pfet", "vro"): 146}:
        raise ValueError(f"{name}: unexpected transistor bodies: {bodies}")
    curated = run(
        ["drc", gds, "--deck", "gf180mcu", "--top", name],
        codes=(3,) if family == "12t" else (0,),
    )
    if curated["rule_counts"] != (library_control if family == "12t" else {}):
        raise ValueError(f"{name}: the curated deck reported additional findings")
    native = run(
        [
            "drc",
            gds,
            "--deck",
            "gf180mcu",
            "--top",
            name,
            *native_options(pdk),
            "--expect-rule-categories-file",
            categories,
        ]
    )
    declared = set(categories.read_text().splitlines())
    if (
        native["status"] != "clean"
        or native["violation_count"] != 0
        or set(native["coverage"]["rules_checked"]) != declared
        or len(declared) != 763
    ):
        raise ValueError(f"{name}: incomplete native DRC")
    layout = db.Layout()
    layout.read(str(gds))
    ports = {}
    for layer in (36, 42):
        for shape in layout.top_cell().shapes(layout.layer(layer, 10)).each():
            if shape.is_text():
                port = shape.text
                ports[port.string] = {"layer": layer, "x_nm": port.x, "y_nm": port.y}
    if set(ports) != set(PUBLIC):
        raise ValueError(f"{name}: incorrect integration ports")
    return {
        "gds_sha256": sha(gds),
        "reference_sha256": sha(stem.with_suffix(".spice")),
        "pex_sha256": sha(pex),
        "bounding_box_nm": str(layout.top_cell().bbox()),
        "port_centres": ports,
        "lvs": counts,
        "feedback_open_lvs": open_counts,
        "body_connections": {"nfet_body_vss": 146, "pfet_body_vro": 146},
        "parasitics": {
            k: ext["parasitics"][k]
            for k in (
                "r_count",
                "c_count",
                "cc_count",
                "total_capacitance_ff",
                "total_coupling_capacitance_ff",
            )
        },
        "native": {
            "status": native["status"],
            "violations": 0,
            "checked_categories": len(declared),
            "deck": native["provenance"]["deck"],
        },
        "curated": {"status": curated["status"], "rules": curated["rule_counts"]},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    pdk = args.pdk.resolve()
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        categories = scratch / "categories.txt"
        cats = subprocess.check_output(
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
        categories.write_text(cats)
        control = library_curated_control(pdk)
        results = {f: check(f, pdk, categories, scratch, control) for f in LIBRARIES}
    report = HERE / "verification.json"
    if args.record:
        report.write_text(json.dumps(results, indent=2) + "\n")
    elif json.loads(report.read_text()) != results:
        raise ValueError("The physical evidence differs from the recorded results")
    print(
        "Reproduced three transistor LVS matches, three feedback opens, three PEX views and all DRC results."
    )


if __name__ == "__main__":
    main()
