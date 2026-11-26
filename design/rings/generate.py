# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14"]
# ///
"""Build the three GF180D oscillator cores from pinned physical library cells."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import urlopen

import klayout.db as db

HERE = Path(__file__).resolve().parent
LIBRARIES = {
    "7t": "gf180mcu_fd_sc_mcu7t5v0",
    "9t": "gf180mcu_fd_sc_mcu9t5v0",
    "12t": "gf180mcu_osu_sc_gp12t3v3",
}
METALS = (34, 36, 42, 46)
VIAS = (35, 38, 40)
PUBLIC = ["en", "out", "vro", "vss"]
FILL_SOURCE = "https://raw.githubusercontent.com/2AMLogic/gf180-efuse-otp/5ff12fe481ca9c52c653896f298aea3241184c51/layout/fill_partitions.py"
FILL_SHA256 = "945cf0d3ebac6e2342eb029c3e293320e28dea642fa928d18b65f8c1916c8c17"
# Locations on the named Metal1 pin islands allowing a 0.4 um landing
# and the GF180D minimum metal spacing to adjacent library conductors.
FOUNDRY_ACCESS = {
    "7t": {
        "inv_1": {"I": (740, 1800), "ZN": (1540, 2040)},
        "nand2_1": {"A1": (1440, 1000), "A2": (740, 2100), "ZN": (2620, 2100)},
        "buf_1": {"I": (920, 1800), "Z": (2640, 1400)},
    },
    "9t": {
        "inv_1": {"I": (740, 1920), "ZN": (1540, 2040)},
        "nand2_1": {"A1": (1880, 2340), "A2": (740, 2100), "ZN": (2160, 1580)},
        "buf_1": {"I": (740, 1980), "Z": (2640, 3080)},
    },
}


def inputs(pdk, family):
    lib = LIBRARIES[family]
    pins = json.loads((HERE / "library-pins.json").read_text())
    paths = {}
    for extension in ("gds", "lef", "spice"):
        name = f"{lib}/{extension}/{lib}.{extension}"
        path = pdk / "libs.ref" / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != pins[name]:
            raise ValueError(f"{path} differs from the pinned open_pdks cell library")
        paths[extension] = path
    return paths


def import_cells(layout, family, paths):
    original = db.Layout()
    original.read(str(paths["gds"]))
    if original.dbu != layout.dbu:
        raise ValueError("Unexpected library database unit")
    lef = paths["lef"].read_text()
    lib = LIBRARIES[family]
    cells, sizes, pins = {}, {}, {}
    names = ["nand2_1", "inv_1", "buf_1"]
    if family != "12t":
        names.append("filltie")
    for name in names:
        full = lib + "__" + name
        source = original.cell(full)
        match = re.search(
            rf"^MACRO {full}\s+.*?\bSIZE ([.\d]+) BY ([.\d]+)", lef, re.M | re.S
        )
        sizes[name] = tuple(round(float(x) / layout.dbu) for x in match.groups())
        target = layout.create_cell(f"ro_{family}__{name}")
        source.flatten(-1, True)
        for index in original.layer_indices():
            layer = original.get_info(index)
            shapes = target.shapes(layout.layer(layer))
            for shape in source.shapes(index).each():
                # Name only the four public conductors on the assembled ring.
                if not shape.is_text() or layer.layer == 63:
                    shapes.insert(shape)
                elif layer.layer in (34, 36) and layer.datatype == 10:
                    pins[name, shape.text.string] = shape.text.trans.disp
        cells[name] = target
    return cells, sizes, pins


def reference(family, source, dest):
    lib = LIBRARIES[family]
    lines = []
    for name in ("nand2_1", "inv_1", "buf_1"):
        pattern = rf"^\.subckt\s+{lib}__{name}\b.*?^\.ends[^\n]*"
        lines.append(re.search(pattern, source, re.I | re.M | re.S).group())
    supplies = "vro vss" if family == "12t" else "vro vro vss vss"
    lines += [
        f".subckt ro_{family} {' '.join(PUBLIC)}",
        f"Xgate n142 en n0 {supplies} {lib}__nand2_1",
        *(f"Xi{i} n{i - 1} n{i} {supplies} {lib}__inv_1" for i in range(1, 143)),
        f"Xbuffer n142 out {supplies} {lib}__buf_1",
        ".ends",
    ]
    dest.write_text("\n".join(lines) + "\n")


def generate(family, pdk, dest, fill_script, scratch):
    paths = inputs(pdk, family)
    layout = db.Layout()
    layout.dbu = 0.001
    top = layout.create_cell("ro_" + family)
    cells, sizes, pins = import_cells(layout, family, paths)
    osu = family == "12t"
    rows = []
    for row in range(12):
        sequence = []
        for col in range(12):
            stage = 12 * row + col
            if not osu and col % 4 == 0:
                sequence.append(("filltie", None))
            name = "nand2_1" if stage == 0 else "buf_1" if stage == 143 else "inv_1"
            sequence.append((name, stage))
        rows.append(sequence)
    width = max(sum(sizes[name][0] for name, _ in row) for row in rows)
    height = sizes["inv_1"][1]

    def box(layer, a, b, thickness):
        half = thickness // 2
        top.shapes(layout.layer(layer, 0)).insert(
            db.Box(
                min(a.x, b.x) - half,
                min(a.y, b.y) - half,
                max(a.x, b.x) + half,
                max(a.y, b.y) + half,
            )
        )

    def route(layer, points, thickness):
        for a, b in zip(points, points[1:]):
            if a.x != b.x and a.y != b.y:
                raise ValueError("Route must be Manhattan")
            box(layer, a, b, thickness)

    def ladder(point, lo, hi):
        for metal in range(lo, hi + 1):
            box(METALS[metal - 1], point, point, 400)
            if metal < hi:
                box(VIAS[metal - 1], point, point, 260)

    def label(metal, point, name):
        top.shapes(layout.layer(metal, 10)).insert(db.Text(name, db.Trans(point)))

    connections = {}
    for row, sequence in enumerate(rows):
        backwards = row % 2 == 1
        x = width if backwards else 0
        for name, stage in sequence:
            trans = db.Trans(
                db.Trans.R180 if backwards else db.Trans.R0,
                x,
                (row + int(backwards)) * height,
            )
            top.insert(db.CellInstArray(cells[name].cell_index(), trans))
            x += sizes[name][0] * (-1 if backwards else 1)
            if stage is None:
                continue
            inputs_ = ("A", "B") if osu else ("A1", "A2")
            pin_map = {
                "input": inputs_[0] if stage == 0 else "A" if osu else "I",
                "output": "Y" if osu else "Z" if stage == 143 else "ZN",
            }
            if stage == 0:
                pin_map["enable"] = inputs_[1]
            for role, pin in pin_map.items():
                point = pins[name, pin]
                if not osu:
                    point = db.Point(*FOUNDRY_ACCESS[family][name][pin])
                point = trans * db.Point(point.x, point.y)
                ladder(point, 2 if osu else 1, 3)
                connections[stage, role] = point
        # OSU puts the two rails inside the LEF boundary. Foundry cells
        # straddle the boundary and share one rail at each mirrored row.
        for positive, edge in ((False, -3600), (True, width + 3600)):
            local = height - 300 if positive else 300
            if not osu:
                local = height if positive else 0
            rail_y = row * height + (height - local if backwards else local)
            joint = db.Point(edge, rail_y)
            route(
                34,
                [joint, db.Point(width - 500 if positive else 500, rail_y)],
                600 if osu else 500,
            )
            if osu:
                # Each OSU implant rail ends in a 0.25 um half strip at the
                # row edge. Close it also at staggered ends and outer edges.
                boundary = (row + int(positive != backwards)) * height
                top.shapes(layout.layer(32 if positive else 31, 0)).insert(
                    db.Box(0, boundary - 250, width, boundary + 250)
                )
            ladder(joint, 1, 2)
    for edge in (-3600, width + 3600):
        route(36, [db.Point(edge, 0), db.Point(edge, height * 12)], 600)
    for stage in range(143):
        a, b = connections[stage, "output"], connections[stage + 1, "input"]
        if stage % 12 == 11:
            x = -1400 if stage // 12 % 2 else width + 1400
            points = [a, db.Point(x, a.y), db.Point(x, b.y), b]
        else:
            points = [a, db.Point(b.x, a.y), b]
        route(42, points, 340)
    a, b = connections[142, "output"], connections[0, "input"]
    for point in (a, b):
        ladder(point, 3, 4)
    route(46, [a, db.Point(-2200, a.y), db.Point(-2200, b.y), b], 400)
    label(42, connections[0, "enable"], "en")
    label(42, connections[143, "output"], "out")
    # Bring the supplies to opposite integration pins. The 15 um perimeter
    # between the compact ring and the outer pins accommodates local fill.
    core = top.bbox()
    for positive, name in ((False, "vss"), (True, "vro")):
        y = (height - 300 if positive else 300) if osu else (height if positive else 0)
        start = db.Point(width + 3600 if positive else -3600, y)
        x = core.right + 15000 if positive else core.left - 15000
        end = db.Point(x, core.top + 15000 if positive else core.bottom - 15000)
        route(36, [start, db.Point(x, y), end], 700)
        label(36, end, name)
    options = db.SaveLayoutOptions()
    options.gds2_write_timestamps = False
    unfilled = scratch / f"ro_{family}.gds"
    filled = scratch / f"filled-{family}.gds"
    layout.write(str(unfilled), options)
    subprocess.run(
        [
            sys.executable,
            fill_script,
            "--input",
            unfilled,
            "--output",
            filled,
            "--top",
            top.name,
            "--report",
            dest / f"ro_{family}.fill.json",
        ],
        check=True,
    )
    final = db.Layout()
    final.read(str(filled))
    final.cell("density_fill").name = f"ro_{family}__density_fill"
    final.write(str(dest / f"ro_{family}.gds"), options)
    reference(family, paths["spice"].read_text(), dest / f"ro_{family}.spice")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdk", type=Path, required=True, help="pinned gf180mcuD directory"
    )
    parser.add_argument("--out", type=Path, default=HERE)
    parser.add_argument(
        "--fill-script",
        type=Path,
        help="offline copy of the pinned GF180 density-fill script",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        if args.fill_script:
            code = args.fill_script.read_bytes()
        else:
            with urlopen(FILL_SOURCE, timeout=30) as response:
                code = response.read()
        if hashlib.sha256(code).hexdigest() != FILL_SHA256:
            raise ValueError(
                "The GF180 density-fill script differs from the pinned revision"
            )
        fill_script = scratch / "fill_partitions.py"
        fill_script.write_bytes(code)
        for family in LIBRARIES:
            generate(family, args.pdk, args.out, fill_script, scratch)


if __name__ == "__main__":
    main()
