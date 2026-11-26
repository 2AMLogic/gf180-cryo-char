# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14"]
# ///
"""Probe OpenROAD's four LEF accesses against the as-streamed GF180D electrodes."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import klayout.db as db
from build import CODES, HERE
from kelvin import export_all

TECH = "libs.ref/gf180mcu_fd_sc_mcu7t5v0/techlef/gf180mcu_fd_sc_mcu7t5v0__nom.tlef"
METAL = {"Metal3": 42, "Metal5": 81}
TERMINAL = {"F1": "Metal5", "S1": "Metal5", "F2": "Metal3", "S2": "Metal3"}


def read_abstract(pdk, tmp):
    # Supply filenames inside the Tcl script as local Docker wrappers may
    # forward the mounted paths without forwarding the host's environment.
    tcl = tmp / "read.tcl"
    tcl.write_text(f"set tech_lef {{{pdk / TECH}}}\n"
                   f"set macro_lef {{{(HERE / 'mim_kelvin.lef').resolve()}}}\n"
                   + (HERE / "read_kelvin_lef.tcl").read_text())
    output = subprocess.check_output(["openroad", "-no_init", "-exit", tcl], text=True)
    sizes, pins, obs = {}, defaultdict(dict), defaultdict(dict)
    for line in output.splitlines():
        fields = line.split()
        if not fields or fields[0] not in {"UNITS", "SIZE", "PIN", "OBS"}:
            continue
        if fields[0] == "UNITS":
            units = int(fields[1])
            continue
        kind, cell = fields[:2]
        coords = fields[2:] if kind == "SIZE" else fields[-4:]
        numbers = [int(value) * 1000 for value in coords]
        if any(value % units for value in numbers):
            raise ValueError("LEF coordinates fall off the GDS database grid")
        values = [value // units for value in numbers]
        if kind == "SIZE":
            sizes[cell] = db.Box(0, 0, *values)
        elif kind == "PIN":
            name, layer = fields[2:4]
            if name in pins[cell]:
                raise ValueError(f"Duplicate access rectangle for {cell}/{name}")
            pins[cell][name] = (layer, db.Box(*values))
        else:
            obs[cell].setdefault(fields[2], db.Region()).insert(db.Box(*values))
    if set(sizes) != {f"mim_{code}_kelvin" for code in CODES}:
        raise ValueError("OpenROAD did not load the four intended macros")
    return sizes, pins, obs


def mask(layout, cell, layer, datatype=0):
    return db.Region(cell.begin_shapes_rec(layout.layer(layer, datatype)))


def access_geometry(layout, cell, bounds, pins, obs):
    if cell.bbox() != bounds or {key: port[0] for key, port in pins.items()} != TERMINAL:
        raise ValueError(f"GDS and LEF differ on dimensions or port names for {cell.name}")
    layers = {"Metal1", "Via1", "Metal2", "Via2", "Metal3", "Via3", "Metal4", "Via4", "Metal5"}
    if set(obs) != layers:
        raise ValueError("Missing routing obstruction layer")
    for layer in layers:
        open_space = db.Region(bounds) - obs[layer]
        if layer not in METAL:
            if not open_space.is_empty():
                raise ValueError(f"Unexpected opening in {layer}")
            continue
        drawn = mask(layout, cell, METAL[layer])
        fill = mask(layout, cell, METAL[layer], 4)
        if not (fill & open_space).is_empty():
            raise ValueError(f"Exposed density fill in a {layer} access")
        # Both access corridors terminate at the macro edge and expose only
        # the corresponding 0.8 µm conductor and its design-rule clearance.
        corridor = db.Region()
        for name, (port_layer, box) in pins.items():
            if port_layer != layer:
                continue
            if not (db.Region(box) - drawn).is_empty():
                raise ValueError(f"LEF pin {name} extends beyond GDS metal")
            corridor.insert(box.enlarged(1000))
        if not (open_space ^ (corridor & db.Region(bounds))).is_empty():
            raise ValueError(f"Routing obstruction differs from the accesses on {layer}")


def probe(cell_name, conductors, sites, plates):
    graph = db.LayoutToNetlist(cell_name, 0.001)
    for key, region in conductors.items():
        graph.register(region, key)
        graph.connect(region)
    # Option B uses a separate upper plate under Via4 inside the MIM marker.
    # An ordinary Via4 elsewhere connects M4 and M5 directly.
    for lower, cut, upper in [("Metal3", "Via3", "Metal4"),
                              ("Plate", "MimVia4", "Metal5"),
                              ("Metal4", "Via4", "Metal5")]:
        graph.connect(conductors[lower], conductors[cut])
        graph.connect(conductors[cut], conductors[upper])
    graph.extract_netlist()

    def cluster(layer, point):
        net = graph.probe_net(conductors[layer], point)
        if net is None:
            raise ValueError(f"No {layer} conductor at {point}")
        return net.cluster_id

    top = cluster("Plate", plates[0])
    bottom = cluster("Metal4", plates[0])
    if top == bottom:
        return {"short"}
    for point in plates[1:]:
        if cluster("Plate", point) != top or cluster("Metal4", point) != bottom:
            raise ValueError(f"Unexpected isolated MIM plate at {point}")
    return {name for name, (layer, point) in sites.items()
            if cluster(layer, point) != (top if layer == "Metal5" else bottom)}


def verify(code, tmp, sizes, abstracts, obstacles, source):
    name = f"mim_{code}_kelvin"
    stream = tmp / f"{name}.gds"
    layout = db.Layout()
    layout.read(str(stream))
    cell = layout.top_cell()
    pins = abstracts[name]
    access_geometry(layout, cell, sizes[name], pins, obstacles[name])
    if hashlib.sha256((HERE / f"mim_{code}.gds").read_bytes()).hexdigest() != source["sha256"]:
        raise ValueError(f"Source no longer matches the dimensional LVS evidence for {name}")

    marker = mask(layout, cell, 75)
    plates = [poly.bbox().center() for poly in marker.each()]
    if len(plates) != source["units"]:
        raise ValueError("Physical MIM count differs from the LVS reference")
    via4 = mask(layout, cell, 41)
    original = {"Metal3": mask(layout, cell, 42), "Via3": mask(layout, cell, 40),
                "Metal4": mask(layout, cell, 46), "Plate": marker,
                "MimVia4": via4 & marker, "Via4": via4 - marker,
                "Metal5": mask(layout, cell, 81)}
    # Add four real horizontal probe traces. Probe the far end outside the
    # macro, so a port marker on a disconnected island cannot pass.
    sites = {}
    for pin, (layer, box) in pins.items():
        x, y = box.center().x, box.center().y
        outside = -8000 if x < 1000 else sizes[name].width() + 8000
        original[layer].insert(db.Box(min(x, outside) - 200, y - 200,
                                      max(x, outside) + 200, y + 200))
        sites[pin] = (layer, db.Point(outside, y))
    if probe(name, original, sites, plates):
        raise ValueError(f"An external access misses its plate in {name}")

    for pin, (layer, box) in pins.items():
        x = box.center().x
        y = 10000 if pin.startswith("F") else sizes[name].height() - 10000
        opened = dict(original)
        opened[layer] = original[layer] - db.Region(db.Box(x - 600, y - 500, x + 600, y + 500))
        if probe(name, opened, sites, plates[:1]) != {pin}:
            raise ValueError(f"Opening {pin} did not isolate exactly that lead in {name}")

    # Deliberately bridge force leads outside the original stream at the south
    # edge. The via stack lies outside the MIM marker and must short the plates.
    shorted = {key: region.dup() for key, region in original.items()}
    a, b = sites["F2"][1], sites["F1"][1]
    shorted["Metal3"].insert(db.Box(a.x - 300, a.y - 300, b.x + 300, b.y + 300))
    for layer, half in (("Via3", 130), ("Metal4", 300), ("Via4", 130)):
        shorted[layer].insert(db.Box(b.x - half, b.y - half, b.x + half, b.y + half))
    if probe(name, shorted, sites, plates[:1]) != {"short"}:
        raise ValueError(f"Deliberate inter-plate short escaped in {name}")
    return {"gds_sha256": hashlib.sha256(stream.read_bytes()).hexdigest(),
            "source_sha256": source["sha256"], "capacitors_probed": len(plates),
            "isolated_by_cut": sorted(pins), "interplate_short_detected": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    source = json.loads((HERE / "verification.json").read_text())
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td).resolve()
        export_all(tmp)
        if (tmp / "mim_kelvin.lef").read_bytes() != (HERE / "mim_kelvin.lef").read_bytes():
            raise ValueError("Generated routing abstract differs from the checked-in LEF")
        sizes, pins, obs = read_abstract(args.pdk.resolve(), tmp)
        report = {str(c): verify(c, tmp, sizes, pins, obs, source[str(c)]) for c in CODES}
    target = HERE / "kelvin-access.json"
    if args.record:
        target.write_text(json.dumps(report, indent=2) + "\n")
    elif report != json.loads(target.read_text()):
        raise ValueError("Kelvin probe evidence changed")
    print("Four macros, 16 independent leads, 16 individual opens and four inter-plate shorts verified.")


if __name__ == "__main__":
    main()
