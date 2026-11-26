"""Verify the committed GF180D readout macro, optionally replaying its full route."""

import argparse
from collections import Counter
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile

import klayout.db as db

FLOW = Path(__file__).resolve().parent
ROOT = FLOW.parent
MACRO = FLOW / "readout"
TOP = "cryo_char_ctrl"
REQUEST = FLOW / "request-par.json"
NETLIST = ROOT / "rtl" / f"{TOP}.gl.v"
AS_BUILT = MACRO / f"{TOP}.asbuilt.v"
FILES = [NETLIST, REQUEST, MACRO / f"{TOP}.def", MACRO / f"{TOP}.gds", AS_BUILT]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def labels(layout, cell, layer):
    factor = round(layout.dbu / 0.0005)
    entries = []
    for shape in cell.shapes(layer).each():
        if shape.is_text():
            entry = shape.text
            transform = entry.trans
            entries.append(
                (
                    entry.string,
                    transform.rot,
                    transform.is_mirror(),
                    transform.disp.x * factor,
                    transform.disp.y * factor,
                )
            )
    return Counter(entries)


def same_masks(original, shipped):
    """The grid conversion can round overlapping source rectangles."""
    if set(c.name for c in original.each_cell()) != set(
        c.name for c in shipped.each_cell()
    ):
        raise ValueError("GDS cells differ after grid conversion")

    def instances(cell, scale):
        return Counter(
            (
                i.cell.name,
                i.cplx_trans.mag,
                i.cplx_trans.angle,
                i.cplx_trans.is_mirror(),
                i.cplx_trans.disp.x * scale,
                i.cplx_trans.disp.y * scale,
                i.a.x * scale,
                i.a.y * scale,
                i.b.x * scale,
                i.b.y * scale,
                i.na,
                i.nb,
            )
            for i in cell.each_inst()
        )

    for cell in original.each_cell():
        if instances(cell, 1) != instances(shipped.cell(cell.name), 2):
            raise ValueError(f"Placement differs in {cell.name}")
    if original.layers() != shipped.layers():
        raise ValueError("Layer count differs after grid conversion")
    for key in original.layer_indices():
        info = original.get_info(key)
        other = shipped.find_layer(info)
        if other is None:
            raise ValueError(f"Missing GDS layer {info}")
        a = db.Region(original.top_cell().begin_shapes_rec(key))
        b = db.Region(shipped.top_cell().begin_shapes_rec(other)).transformed(
            db.ICplxTrans(2, 0, False, 0, 0)
        )
        if not (a.merged() ^ b.merged()).is_empty():
            raise ValueError(f"Drawn masks differ on {info}")
        for cell in original.each_cell():
            if labels(original, cell, key) != labels(
                shipped, shipped.cell(cell.name), other
            ):
                raise ValueError(f"Labels differ in {cell.name} on {info}")


def shuttle_stream(source, dest):
    original = db.Layout()
    original.read(str(source))
    if original.top_cell().name != TOP or original.dbu != 0.0005:
        raise ValueError("Unexpected source top or layout grid")
    options = db.SaveLayoutOptions()
    options.dbu = 0.001
    options.gds2_write_timestamps = False
    original.write(str(dest), options)
    shipped = db.Layout()
    shipped.read(str(dest))
    if shipped.top_cell().name != TOP or shipped.dbu != 0.001:
        raise ValueError("Unexpected output top or shuttle grid")
    same_masks(original, shipped)


def check_files():
    observed = {f.relative_to(ROOT).as_posix(): sha(f) for f in FILES}
    record = json.loads((MACRO / "route.json").read_text())
    if observed != record["sha256"]:
        bad = [
            name
            for name in sorted(observed.keys() | record["sha256"].keys())
            if observed.get(name) != record["sha256"].get(name)
        ]
        raise ValueError("Source or routed artifact changed: " + ", ".join(bad))
    return record


def route(destination, record):
    cfg = json.loads(REQUEST.read_text())
    (destination / "flow").mkdir()
    (destination / "rtl").mkdir()
    shutil.copyfile(NETLIST, destination / "rtl" / NETLIST.name)
    req = destination / "flow" / REQUEST.name
    req.write_bytes(REQUEST.read_bytes())
    if (req.parent / cfg["netlist"]).resolve() != destination / "rtl" / NETLIST.name:
        raise ValueError("P&R recipe does not use the checked controller netlist")
    klt = os.environ.get("KLT", "klt")
    with (destination / "route.json").open("w") as log:
        subprocess.run(
            [
                klt,
                "place-and-route",
                str(req),
                "--pdk",
                "gf180mcuD",
                "--format",
                "json",
            ],
            check=True,
            cwd=destination,
            stdout=log,
        )
    report = json.loads((destination / "route.json").read_text())
    if (
        report["status"],
        report["stage_reached"],
        report["route_drc_violation_count"],
    ) != ("ok", "route", 0):
        raise ValueError("OpenROAD did not complete a clean detailed route")
    if (
        report["provenance"]["klt_git_commit"]
        != "4f24005b034d55051ddeded1510ef4b9d185554d"
    ):
        raise ValueError("Use the recorded nine-clock KLT implementation revision")

    # The portable report can elide paths outside a checkout. The request
    # selects this directory, and the flow names each output after the top.
    out = req.parent / cfg["outputs"]["dir"]
    cts_log = next(
        log
        for log in report["engine_logs"]
        if log["script_name"] == f"pnr_{TOP}_cts.tcl"
    )
    cts_text = (
        out / "openroad-logs" / cts_log["invocation_id"] / "stdout.log"
    ).read_text()
    sinks = {
        port: int(count)
        for port, count in re.findall(r'Clock net "([^"]+)" has (\d+) sinks', cts_text)
    }
    observed = {
        "engine_version": report["engine_version"],
        "pdk": report["provenance"]["pdk"]["version"],
        "source_dbu_um": report["gds_dbu_um"],
        "shipped_dbu_um": 0.001,
        "core_area_um2": report["core_area_um2"],
        "die_area_um2": report["die_area_um2"],
        "route_drc_violation_count": report["route_drc_violation_count"],
        "global_connect": report["power"]["global_connect"],
        "pdn": report["power"]["pdn"],
        "placed_components": report["power"]["placed"]["components"],
        "placed_taps": report["power"]["placed"]["tapcells"],
        "cts_sinks": sinks,
    }
    if observed != {key: value for key, value in record.items() if key != "sha256"}:
        raise ValueError(f"Fresh route metrics diverge from route.json: {observed}")
    if report["provenance"]["input"]["content_hash"] != "sha256:" + sha(NETLIST):
        raise ValueError("P&R used a different netlist")
    shipped = destination / f"{TOP}.gds"
    shuttle_stream(out / f"{TOP}.gds", shipped)
    for actual, expected in (
        (shipped, MACRO / f"{TOP}.gds"),
        (out / f"{TOP}.def", MACRO / f"{TOP}.def"),
        (out / f"{TOP}.v", AS_BUILT),
    ):
        if sha(actual) != sha(expected):
            raise ValueError(f"Fresh {actual.name} differs from {expected.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reroute",
        action="store_true",
        help="run the pinned OpenROAD implementation as well",
    )
    args = parser.parse_args()
    record = check_files()
    if args.reroute:
        with tempfile.TemporaryDirectory() as workspace:
            route(Path(workspace).resolve(), record)
    print("Routed GF180D readout macro verified.")


if __name__ == "__main__":
    main()
