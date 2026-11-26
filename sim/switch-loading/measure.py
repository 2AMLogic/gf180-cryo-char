"""Measure terminal current and its BSIM components on the single-switch control."""

import argparse
import csv
import io
import itertools
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "spec/switch-reference.spice"
sys.path.insert(0, str(HERE.parent))
from qualification_pdk import check_inputs

VECTORS = {
    "terminal_a": "i(vsense)",
    "pmos_igisl_a": "@m.xp.m0[igisl]",
    "pmos_igidl_a": "@m.xp.m0[igidl]",
    "pmos_ibs_a": "@m.xp.m0[ibs]",
    "pmos_id_a": "@m.xp.m0[id]",
    "nmos_id_a": "@m.xn.m0[id]",
    "nmos_ibs_a": "@m.xn.m0[ibs]",
    "nmos_igidl_a": "@m.xn.m0[igidl]",
    "nmos_igisl_a": "@m.xn.m0[igisl]",
}
BIASES = tuple(itertools.product((0, 3.3), (3.3, 2.75, 2.2, 1.65)))


def measured_rows(pdk, simulator):
    version = subprocess.check_output([simulator, "--version"], text=True)
    if not re.search(r"ngspice-(46|47)\b", version):
        raise ValueError("Use ngspice 46 or 47")
    reference = SOURCE.read_text().split(".control")[0]
    # Keep the well on its original independent 3.3 V rail throughout.
    if reference.count("Xp far rail measured rail") != 1:
        raise ValueError("The reference switch topology has changed")
    template = reference.replace(
        "Xp far rail measured rail", "Vpg pg 0 3.3\nXp far pg measured rail"
    )
    controls = [".control", "set numdgt=12"]
    for far, gate in BIASES:
        controls.extend(
            [
                f"alter Vfar = {far}",
                f"alter Vpg = {gate}",
                "op",
                "print " + " ".join(VECTORS.values()),
            ]
        )
    controls.extend(["quit", ".endc", ".end", ""])
    with tempfile.TemporaryDirectory() as tempdir:
        work = Path(tempdir)
        (work / "pdk").symlink_to(pdk, target_is_directory=True)
        for corner, temperature in itertools.product(
            ("typical", "ff", "ss", "fs", "sf"), (-40, 25, 125)
        ):
            bench = template.replace(".ngspice typical", ".ngspice " + corner)
            bench = bench.replace(".temp 25", f".temp {temperature}")
            (work / "probe.cir").write_text(bench + "\n".join(controls))
            run = subprocess.run(
                [simulator, "-b", "probe.cir"],
                cwd=work,
                text=True,
                capture_output=True,
                check=True,
            )
            samples = {}
            for label, vector in VECTORS.items():
                values = re.findall(
                    r"^" + re.escape(vector) + r"\s*=\s*([-+0-9.eE]+)\s*$",
                    run.stdout,
                    re.MULTILINE,
                )
                if len(values) != len(BIASES):
                    raise ValueError(
                        f"Incomplete {corner}/{temperature} {vector}: {run.stderr}"
                    )
                samples[label] = values
            for i, (far, gate) in enumerate(BIASES):
                yield {
                    "process": corner,
                    "temperature_c": temperature,
                    "far_v": far,
                    "pmos_gate_v": gate,
                    **{k: v[i] for k, v in samples.items()},
                }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", required=True, type=Path)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--output", type=Path, help="write a new measurement file")
    args = parser.parse_args()
    pdk = args.pdk.resolve()
    check_inputs(pdk, include_pad=False)
    rows = list(measured_rows(pdk, args.ngspice))
    stream = io.StringIO()
    output = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    output.writeheader()
    output.writerows(rows)
    if args.output:
        args.output.write_text(stream.getvalue())
    else:
        with (HERE / "measurements.csv").open() as reference:
            old = list(csv.DictReader(reference))
        if len(old) != len(rows):
            raise ValueError("Grid size changed")
        for a, b in zip(rows, old):
            for key in a:
                if key in VECTORS:
                    matches = math.isclose(
                        float(a[key]), float(b[key]), rel_tol=1e-4, abs_tol=1e-19
                    )
                else:
                    matches = str(a[key]) == b[key]
                if not matches:
                    raise ValueError(
                        f"Changed {key} at {a['process']}/{a['temperature_c']}/{a['far_v']}/{a['pmos_gate_v']}"
                    )
        print(f"Reproduced {len(rows)} switch bias and PVT points.")


if __name__ == "__main__":
    main()
