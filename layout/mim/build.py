# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14"]
# ///
"""Place, route and fill the four MIM specimens from the characterization map."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen

import klayout.db as db

HERE = Path(__file__).resolve().parent
CODES = (452, 453, 454, 455)
FILL_URL = "https://raw.githubusercontent.com/2AMLogic/gf180-efuse-otp/5ff12fe481ca9c52c653896f298aea3241184c51/layout/fill_partitions.py"
FILL_SHA256 = "945cf0d3ebac6e2342eb029c3e293320e28dea642fa928d18b65f8c1916c8c17"


def dimensions(code):
    # Plate side, centre pitch, columns, rows and repeated windows in X/Y, in µm.
    if code in (452, 453):
        return 40, 44, 5, 1, 1, 1
    if code == 454:
        return 5, 12.4, 14, 14, 5, 4
    if code == 455:
        return 10, 20, 9, 9, 5, 4
    raise ValueError(f"Unknown MIM code {code}")


def options():
    opts = db.SaveLayoutOptions()
    opts.gds2_write_timestamps = False
    return opts


def assemble(code, units, output):
    side, pitch, columns, rows, across, down = dimensions(code)
    layout = db.Layout()
    layout.dbu = 0.001
    seed = db.Layout()
    seed.read(str(units / f"{side}.gds"))
    unit = layout.create_cell(f"cryo_mim_{side}")
    unit.copy_tree(seed.top_cell())
    # Take each lower plate down separately. A common continuous Metal4 plate
    # would exceed MIMTM.11 on the two perimeter specimens.
    tap_x = side / 2 + 1.25
    unit.shapes(layout.layer(46, 0)).insert(db.DBox(side / 2, -0.3, tap_x + 0.3, 0.3))
    unit.shapes(layout.layer(42, 0)).insert(
        db.DBox(tap_x - 0.3, -0.3, tap_x + 0.3, 0.3)
    )
    unit.shapes(layout.layer(40, 0)).insert(
        db.DBox(tap_x - 0.13, -0.13, tap_x + 0.13, 0.13)
    )
    top = layout.create_cell(f"mim_{code}")
    # Standalone cell DRC enforces global density over the macro extent (DCF.1b
    # >= 25% COMP, PL.8 >= 14% Poly2, M1.4-M5.4 / MT.3 > 30% metal), while DM.8
    # requires 6 um from dummy metal to FuseTop (75/0, the option-B top plate)
    # and fill_partitions.py applies the same 6 um FuseTop halo to FEOL fill.
    # Inside each 14x14 (166.2 um) or 9x9 (170.0 um) window, adjacent FuseTop
    # plates sit 7.4 um or 10.0 um apart (< 12 um), excluding all fill inside
    # the windows. A bare 175 um window pitch leaves 8.8 um / 5.0 um between
    # windows (< 12 um) and fails standalone density (M3.4 15.13% / 13.64%).
    # With the 0.8 um Metal3 row buses (DM.3 2 um halo), code 455 first clears
    # M3.4 > 30% at 249 um pitch (30.02%); 260 um gives ~2% M3.4 margin (32.24%
    # on 454, 32.33% on 455). Anchoring each grid at (260*ix, 260*iy) omits the
    # unmarked 175 um frame (a uniform 4.4 / 2.5 um translation absorbed by the
    # outer bus margins with identical inter-plate and inter-window spacing).
    xs = [260 * window + pitch * i for window in range(across) for i in range(columns)]
    ys = [260 * window + pitch * i for window in range(down) for i in range(rows)]
    for iy in range(down):
        for ix in range(across):
            top.insert(
                db.CellInstArray(
                    unit.cell_index(),
                    db.Trans(260000 * ix, 260000 * iy),
                    db.Vector(round(pitch * 1000), 0),
                    db.Vector(0, round(pitch * 1000)),
                    columns,
                    rows,
                )
            )

    def wire(layer, x0, y0, x1, y1):
        path = db.DPath([db.DPoint(x0, y0), db.DPoint(x1, y1)], 0.8)
        top.shapes(layout.layer(layer, 0)).insert(path.polygon())

    left, right = xs[0] - side / 2 - 35, xs[-1] + side / 2 + 35
    for y in ys:
        wire(42, left, y, xs[-1] + tap_x, y)
        wire(81, xs[0], y, right, y)
    for layer, x, pin in ((42, left, "bot"), (81, right, "top")):
        lower = ys[0] - side / 2 - 45
        wire(layer, x, lower, x, ys[-1] + side / 2 + 45)
        top.shapes(layout.layer(layer, 10)).insert(
            db.DText(pin, db.DTrans(x, lower + 1))
        )
    layout.write(str(output), options())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--units", type=Path, help="existing output from glayout_units.py"
    )
    parser.add_argument(
        "--fill-script", type=Path, help="offline copy of the pinned fill generator"
    )
    args = parser.parse_args()
    args.output.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory() as scratch:
        tmp = Path(scratch)
        units = args.units or tmp / "units"
        if not args.units:
            subprocess.run(
                ["uv", "run", "--script", HERE / "glayout_units.py", units], check=True
            )
        if args.fill_script:
            fill = args.fill_script.resolve()
        else:
            fill = tmp / "fill_partitions.py"
            with urlopen(FILL_URL, timeout=30) as response:
                fill.write_bytes(response.read())
        if hashlib.sha256(fill.read_bytes()).hexdigest() != FILL_SHA256:
            raise ValueError("Fill generator digest differs")
        for code in CODES:
            name = f"mim_{code}"
            raw = tmp / f"{name}.gds"
            filled = tmp / f"{name}.filled.gds"
            assemble(code, units, raw)
            subprocess.run(
                [
                    sys.executable,
                    fill,
                    "--input",
                    raw,
                    "--output",
                    filled,
                    "--top",
                    name,
                    "--report",
                    tmp / f"{name}.fill.json",
                ],
                check=True,
            )
            layout = db.Layout()
            layout.read(str(filled))
            layout.cell("density_fill").name = f"{name}__density_fill"
            layout.write(str(args.output / f"{name}.gds"), options())


if __name__ == "__main__":
    main()
