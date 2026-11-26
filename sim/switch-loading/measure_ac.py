"""Measure the AC loading of parallel open reference switches at the T4 stimulus."""

import argparse
import csv
from itertools import product
from math import hypot, isclose, pi
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from qualification_pdk import check_inputs

SOURCE = HERE.parents[1] / "spec/switch-reference.spice"


def measure(pdk, simulator):
    check_inputs(pdk, include_pad=False)
    version = subprocess.check_output([simulator, "--version"], text=True)
    if not re.search(r"ngspice-(46|47)\b", version):
        raise ValueError("Use ngspice 46 or 47")
    template = SOURCE.read_text().split(".control")[0]
    devices = [
        line for line in template.splitlines() if line.startswith(("Xn ", "Xp "))
    ]
    if len(devices) != 2:
        raise ValueError("Expected the two open-switch device cards")
    base = "\n".join(line for line in template.splitlines() if line not in devices)
    base = base.replace("Vsense measured 0 0", "Vsense measured 0 DC 0 AC 0.01")
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch)
        (path / "pdk").symlink_to(pdk)
        for corner, temp, far, branches in product(
            ("typical", "ff", "ss", "fs", "sf"), (-40, 25, 125), (0, 3.3), (0, 1, 4)
        ):
            netlist = base.replace(".ngspice typical", ".ngspice " + corner)
            netlist = netlist.replace(".temp 25", f".temp {temp}").replace(
                "Vfar far 0 3.3", f"Vfar far 0 {far}"
            )
            cards = [
                card.replace(" ", f"{i} ", 1)
                for i in range(branches)
                for card in devices
            ]
            text = "\n".join(
                [
                    netlist,
                    *cards,
                    ".control",
                    "set numdgt=12",
                    "ac lin 1 10k 10k",
                    "let ir = -real(i(vsense))",
                    "let ii = -imag(i(vsense))",
                    "print ir ii",
                    "quit",
                    ".endc",
                    ".end",
                    "",
                ]
            )
            (path / "probe.cir").write_text(text)
            proc = subprocess.run(
                [simulator, "-n", "-b", "probe.cir"],
                cwd=path,
                capture_output=True,
                text=True,
                check=True,
            )
            currents = [
                float(re.search(rf"(?m)^{name}\s*=\s*([-+\d.eE]+)$", proc.stdout)[1])
                for name in ("ir", "ii")
            ]
            yield dict(
                process=corner,
                temperature_c=temp,
                far_v=far,
                branches=branches,
                real_a=currents[0],
                imag_a=currents[1],
                magnitude_pa=hypot(*currents) * 1e12,
                equivalent_cap_ff=currents[1] * 1e15 / (2 * pi * 10000 * 0.01),
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", required=True, type=Path)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = list(measure(args.pdk.resolve(), args.ngspice))
    for i in range(0, len(rows), 3):
        empty, single, four = rows[i : i + 3]
        if empty["magnitude_pa"] != 0 or single["magnitude_pa"] <= 0:
            raise ValueError(f"Empty or connected AC control failed at {single}")
        for key in ("real_a", "imag_a"):
            if not isclose(four[key], 4 * single[key], rel_tol=1e-6, abs_tol=1e-21):
                raise ValueError(
                    f"Parallel switch population control failed at {single}"
                )
    if args.output:
        with args.output.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    else:
        with (HERE / "ac-loading.csv").open() as stream:
            saved = list(csv.DictReader(stream))
        for old, fresh in zip(saved, rows, strict=True):
            for key, value in fresh.items():
                if key in ("process", "temperature_c", "far_v", "branches"):
                    agrees = str(value) == old[key]
                else:
                    agrees = isclose(
                        float(old[key]), value, rel_tol=1e-5, abs_tol=1e-21
                    )
                if not agrees:
                    raise ValueError(f"Changed {key} in {old}")
    print(f"{len(rows)} AC measurements including disconnected controls")


if __name__ == "__main__":
    main()
