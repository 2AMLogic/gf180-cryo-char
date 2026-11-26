"""Replay the GF180D asig_5p0 clamp loading on one powered measurement pad."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import itertools
import math
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
PAD = "gf180mcu_fd_io__asig_5p0"
PINS = {
    "libs.ref/gf180mcu_fd_io/spice/gf180mcu_fd_io.spice": "710732fd6a69e165caa2c29e4cdf81b11af41da32705fcd860b7ecfb09630dd1",
    "libs.tech/ngspice/design.ngspice": "7e222f050318388f37543a64fbd0be55cc15e4b93f57501a09f7c159c4c9e561",
    "libs.tech/ngspice/sm141064.ngspice": "f6f4a96e18fc5ad11270ad3451aaecc7ac37fc81eb61e15b0d7d94c7bc594a24",
    "libs.tech/ngspice/sm141064.spice": "f6f4a96e18fc5ad11270ad3451aaecc7ac37fc81eb61e15b0d7d94c7bc594a24",
}


def reading(output, name):
    found = re.findall(r"(?m)^" + re.escape(name) + r"\s*=\s*([-+\d.eE]+)\s*$", output)
    if len(found) != 1 or not math.isfinite(value := float(found[0])):
        raise ValueError(f"Missing or ambiguous simulator reading {name}")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    pdk = args.pdk.resolve()
    if not re.search(
        r"ngspice-46\b", subprocess.check_output([args.ngspice, "--version"], text=True)
    ):
        parser.error("Use ngspice 46")
    if (
        pdk / "SOURCES"
    ).read_text().strip() != "open_pdks f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7":
        parser.error("Use the pinned GF180D open_pdks install")
    for file, digest in PINS.items():
        if hashlib.sha256((pdk / file).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Unexpected PDK file {file}")
    io = (pdk / next(iter(PINS))).read_text()
    cells = re.findall(rf"(?ms)^\.SUBCKT {PAD} [^\n]+\n.*?^\.ENDS[^\n]*\n", io)
    if len(cells) != 1:
        raise ValueError("Expected one exact foundry pad subcircuit")
    # Copy only the two pad-facing diode cards onto a separate ideal-voltage node.
    # The rail clamp and the MOS bypass do not touch ASIG5V.
    separate = []
    for line in cells[0].splitlines():
        if line.startswith(("D2 ", "D3 ")):
            name, pos, neg, *model = line.split()
            nodes = {"DVSS": "0", "DVDD": "supply", "ASIG5V": "clamps"}
            separate.append(" ".join([name, nodes[pos], nodes[neg], *model]))
    if len(separate) != 2:
        raise ValueError("Unexpected pad clamp topology")
    clamp_cards = "\n".join(separate)
    models = pdk / "libs.tech/ngspice"

    def point(case):
        corner, temp, rail, fraction, gmin = case
        bias = round(rail * fraction, 6)
        deck = f"""One GF180D measurement pad with ideal rails and no DUT or switch
.include "{models}/design.ngspice"
.lib "{models}/sm141064.ngspice" diode_{corner}
.lib "{models}/sm141064.ngspice" moscap_{corner}
{cells[0]}
Vrail supply 0 {rail}
Vm pad 0 DC {bias} AC 0.01
Xpad pad supply 0 supply 0 {PAD}
Vcheck clamps 0 DC {bias}
{clamp_cards}
.temp {temp}
.options gmin={gmin} abstol=1e-22 reltol=1e-7
.control
set numdgt=14
op
print i(vm) @d.xpad.d2[id] @d.xpad.d3[id] @d2[id] @d3[id]
ac lin 1 10000 10000
let cpad = -imag(i(vm))/(2*pi*10000*0.01)
print cpad
quit
.endc
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "pad.cir"
            f.write_text(deck)
            run = subprocess.run(
                [args.ngspice, "-n", "-b", f],
                text=True,
                capture_output=True,
                check=True,
            )
        if re.search(r"(?im)^\s*(error|fatal)\b", run.stdout + run.stderr):
            raise ValueError(f"ngspice failed at {case}")
        d2 = reading(run.stdout, "@d.xpad.d2[id]")
        d3 = reading(run.stdout, "@d.xpad.d3[id]")
        net = d2 - d3
        current = reading(run.stdout, "i(vm)")
        capacitance = reading(run.stdout, "cpad")
        for branch, separately in ((d2, "@d2[id]"), (d3, "@d3[id]")):
            if not math.isclose(
                branch, reading(run.stdout, separately), rel_tol=1e-5, abs_tol=1e-19
            ):
                raise ValueError(f"Isolated diode and full pad differ at {case}")
        if not 0 < capacitance < 1e-9:
            raise ValueError(f"No finite pad capacitance at {case}")
        return dict(
            diode_corner=corner,
            temp_c=temp,
            dvdd_v=rail,
            pad_v=bias,
            gmin_s=gmin,
            d2_a=d2,
            d3_a=d3,
            clamp_net_a=net,
            source_a=current,
            capacitance_f=capacitance,
        )

    grid = [
        (p, t, v, f, 1e-18)
        for p, t, v, f in itertools.product(
            ("typical", "ss", "ff"),
            (-40, 25, 125),
            (3.0, 3.3, 3.6),
            (0, 0.25, 0.5, 0.75, 1),
        )
    ]
    grid.extend(
        ("typical", t, 3.3, f, g)
        for t, f, g in itertools.product((-40, 25, 125), (0, 0.5, 1), (1e-12, 1e-21))
    )
    with ThreadPoolExecutor(args.jobs) as workers:
        rows = list(workers.map(point, grid))
    target = HERE / "measurements.csv"
    if args.write:
        with target.open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=list(rows[0]), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
    else:
        with target.open() as stream:
            saved = list(csv.DictReader(stream))
        if len(saved) != len(rows):
            raise ValueError("Pad sweep coverage changed")
        for previous, fresh in zip(saved, rows):
            for key, value in fresh.items():
                if key in ("diode_corner", "temp_c", "dvdd_v", "pad_v", "gmin_s"):
                    matches = str(value) == previous[key]
                else:
                    matches = math.isclose(
                        value, float(previous[key]), rel_tol=2e-5, abs_tol=2e-17
                    )
                if not matches:
                    raise ValueError(f"Changed pad result at {fresh} ({key})")
    print(f"{len(rows)} powered-pad DC and AC measurements")


if __name__ == "__main__":
    main()
