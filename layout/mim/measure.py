# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14", "klayout-tools==0.9.2"]
# ///
"""Measure the small-signal capacitance of every extracted MIM bank at the T4 stimulus."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import itertools
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

from build import CODES, HERE
from verify import KLT, check_toolchain, run

MODELS = {
    "design.ngspice": "7e222f050318388f37543a64fbd0be55cc15e4b93f57501a09f7c159c4c9e561",
    "sm141064.ngspice": "f6f4a96e18fc5ad11270ad3451aaecc7ac37fc81eb61e15b0d7d94c7bc594a24",
    "sm141064_mim.ngspice": "9b85cd009968d9aeb6b61046b24a63f39d6a463c4e4aee3949c8fd183c06666f",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", required=True, type=Path)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--output", type=Path, help="write fresh results to this CSV")
    args = parser.parse_args()
    sim = os.getenv("NGSPICE", "ngspice")
    if args.jobs < 1 or "ngspice-47 " not in subprocess.check_output(
        [sim, "--version"], text=True
    ):
        parser.error("A positive job count and ngspice 47 are required")
    pdk = args.pdk.absolute()
    check_toolchain(KLT, pdk)
    models = pdk / "libs.tech/ngspice"
    for file, sha in MODELS.items():
        if hashlib.sha256((models / file).read_bytes()).hexdigest() != sha:
            raise ValueError(f"Unexpected model {file}")
    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch)
        for code in CODES:
            name = f"mim_{code}"
            run(
                [
                    "extract",
                    HERE / f"{name}.gds",
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
                    "top,bot",
                    "--rename-declared-pins",
                    "-o",
                    work / f"{name}.spice",
                ]
            )

        def point(case):
            code, corner, temp, bias = case
            lines = [
                "GF180D MIM array admittance",
                f'.include "{models}/design.ngspice"',
                f'.lib "{models}/sm141064.ngspice" {corner}',
                f'.include "{work}/mim_{code}.spice"',
                ".param sw_stat_global=0",
                f".temp {temp}",
                f"Vdrive top 0 DC {bias} AC 0.01",
                f"Xbank top 0 mim_{code}",
                ".control",
                "set numdgt=12",
                "ac lin 1 10k 10k",
                "let capacitance = -imag(i(vdrive))/(2*pi*10000*0.01)",
                "print capacitance",
                "quit",
                ".endc",
                ".end",
            ]
            deck = work / f"{code}-{corner}-{temp}-{bias}.cir"
            deck.write_text("\n".join(lines) + "\n")
            proc = subprocess.run(
                [sim, "-b", deck], capture_output=True, text=True, check=True
            )
            match = re.search(r"(?m)^capacitance\s*=\s*([-+eE\d.]+)$", proc.stdout)
            if not match or not (0 < (cap := float(match[1])) < 1e-6):
                raise ValueError(
                    f"No valid AC capacitance for {case}: {proc.stderr[-300:]}"
                )
            return dict(
                code=code,
                mim_corner=corner,
                temp_c=temp,
                bias_v=bias,
                capacitance_pf=cap * 1e12,
            )

        grid = itertools.product(
            CODES,
            ("mimcap_ff", "mimcap_typical", "mimcap_ss"),
            (-40, 25, 125),
            (0, 1.65, 3.3),
        )
        with ThreadPoolExecutor(args.jobs) as pool:
            rows = list(pool.map(point, grid))
    if args.output:
        with args.output.open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=list(rows[0]), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
    else:
        with (HERE / "measurements.csv").open() as stream:
            saved = list(csv.DictReader(stream))
        if len(saved) != len(rows):
            raise ValueError("AC coverage changed")
        for prior, fresh in zip(saved, rows):
            if any(
                str(fresh[k]) != prior[k]
                for k in ("code", "mim_corner", "temp_c", "bias_v")
            ) or not math.isclose(
                fresh["capacitance_pf"], float(prior["capacitance_pf"]), rel_tol=1e-5
            ):
                raise ValueError(f"AC point differs: {fresh}")
        print(f"Replayed {len(rows)} extracted AC measurements at 10 kHz and 10 mV.")


if __name__ == "__main__":
    main()
