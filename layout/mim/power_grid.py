# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14", "klayout-tools==0.9.2"]
# ///
"""Generate the macro-aware upper power mesh and extract its physical connectivity."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import klayout.db as db
from verify_kelvin import CODES, HERE, TECH, check_toolchain

LAYERS = ("Metal4", "Via4", "Metal5")
RAILS = ("VDD", "VSS")


def components(regions, units):
    graph = db.LayoutToNetlist("mesh", 1 / units)
    for layer, region in zip(LAYERS, regions):
        graph.register(region, layer)
        graph.connect(region)
    graph.connect(regions[0], regions[1])
    graph.connect(regions[1], regions[2])
    graph.extract_netlist()
    return sum(1 for _ in graph.netlist().top_circuit().each_net())


def template_core_nm():
    """The template's snapped core box, the one authoritative record in-repo."""
    return json.loads((HERE / "template-grid.json").read_text())["core_nm"]


def analyze(geometry):
    meshes = {rail: {layer: db.Region() for layer in LAYERS} for rail in RAILS}
    macros = {}
    with geometry.open() as stream:
        tag, count = next(stream).split()
        if tag != "UNITS" or int(count) <= 0:
            raise ValueError("Missing OpenROAD database units")
        units = int(count)
        for line in stream:
            owner, name, *coords = line.split()
            box = db.Box(*map(int, coords))
            if owner == "MACRO":
                if name in macros:
                    raise ValueError(f"Duplicate macro {name}")
                macros[name] = box
            else:
                meshes[owner][name].insert(box)
    if set(macros) != {f"mim_{code}_kelvin" for code in CODES}:
        raise ValueError("Missing Kelvin specimen")
    core_nm = template_core_nm()
    core = db.Box(*(round(v * units / 1000) for v in core_nm))
    if any((core & b) != b for b in macros.values()) or any(
        a.overlaps(b) for a, b in itertools.combinations(macros.values(), 2)
    ):
        raise ValueError("Overlapping or out-of-core macros")
    counts = {}
    outline = db.Region()
    for box in macros.values():
        outline.insert(box)
    contacts = 0
    for rail, regions in meshes.items():
        counts[rail] = {name: region.count() for name, region in regions.items()}
        contacts += sum(r.interacting(outline).count() for r in regions.values())
        if any(r.is_empty() for r in regions.values()) or contacts:
            raise ValueError(f"{rail} geometry is absent or touches a specimen outline")
        if components(list(regions.values()), units) != 1:
            raise ValueError(f"Disconnected {rail} mesh")

    positive, ground = (meshes[rail] for rail in RAILS)
    combined = [positive[name] + ground[name] for name in LAYERS]
    net_count = components(combined, units)
    if net_count != 2:
        raise ValueError("Upper mesh extraction joined both supplies")
    # Deliberately join unlike rails at a real crossing, then separately remove
    # every VSS cut. Both faults must change the extracted component count.
    crossing = next((p.bbox().center() for p in (positive["Metal4"] & ground["Metal5"]).each()), None)
    if crossing is None:
        raise ValueError("No physical VDD/VSS crossing for the short control")
    bridge = db.Region(db.Box(crossing, crossing).enlarged(units // 4))
    short = components([combined[0], combined[1] + bridge, combined[2]], units)
    opened = components([combined[0], positive["Via4"], combined[2]], units)
    if short != 1 or opened <= 2:
        raise ValueError(f"Undetected physical control: short={short} open={opened}")
    return {
        "dbu_per_um": units,
        "macro_bboxes_dbu": {key: [b.left, b.bottom, b.right, b.top] for key, b in sorted(macros.items())},
        "upper_supply_shapes": counts,
        "core_dbu": [core.left, core.bottom, core.right, core.top],
        "macro_outline_contacts": contacts,
        "extracted_supply_nets": net_count,
        "inserted_cross_rail_via_nets": short,
        "removed_vss_vias_nets": opened,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pdk", type=Path, required=True)
    args = p.parse_args()
    pdk = args.pdk.resolve()
    check_toolchain(Path(sys.executable).with_name("klt"), pdk, require_openroad=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp).resolve()
        input_files = {"tech_lef": pdk / TECH, "macro_lef": HERE / "mim_kelvin.lef",
                       "verilog": HERE / "power_grid.v"}
        geometry = work / "geometry.txt"
        command = work / "generate.tcl"
        paths = {**input_files, "geometry": geometry}
        core_um = " ".join(f"{v / 1000:g}" for v in template_core_nm())
        command.write_text("".join(f"set {key} {{{path}}}\n" for key, path in paths.items())
                           + f"set core_area {{{core_um}}}\n"
                           + (HERE / "power_grid.tcl").read_text())
        log = subprocess.check_output(["openroad", "-no_init", "-exit", command], text=True)
        if "[WARNING PDN-" in log or not all(f"All shapes on net {r} are connected." in log for r in RAILS):
            raise ValueError(f"OpenROAD power-grid check failed\n{log}")
        report = analyze(geometry)
        report["inputs_sha256"] = {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in {**input_files, "grid_tcl": HERE / "power_grid.tcl"}.items()
        }
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
