"""Measure local mismatch on four inactive reference branches at fixed process corners."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from math import comb, hypot, isclose, isfinite
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from qualification_pdk import check_inputs

SOURCE = HERE.parents[1] / "spec/switch-reference.spice"
SEEDS = range(1001, 1129)
# The hot FF case maximizes DC loading and AC magnitude in the deterministic grid.
# Swapping the two terminal biases exercises current into the opposite instrument.
CASES = (
    ("typical", 25, 0, 0),
    ("ff", 125, 0, 3.3),
    ("ff", 125, 3.3, 0),
)
COLUMNS = ("process", "temp_c", "sense_v", "far_v", "seed", "dc_a", "real_a", "imag_a")


def measure(pdk, simulator, case, seed, mismatch=1, branches=4):
    corner, temperature, sense, far = case
    original = SOURCE.read_text().split(".control")[0].splitlines()
    cards = [line for line in original if line.startswith(("Xn ", "Xp "))]
    if len(cards) != 2:
        raise ValueError("Expected one NMOS and one PMOS card")
    base = "\n".join(line for line in original if line not in cards)
    base = base.replace(".ngspice typical", f".ngspice {corner}")
    base = base.replace(".temp 25", f".temp {temperature}")
    base = base.replace("Vfar far 0 3.3", f"Vfar far 0 {far}")
    base = base.replace("Vsense measured 0 0", f"Vsense measured 0 DC {sense} AC 0.01")
    base = base.replace(
        "sw_stat_global=0", f"sw_stat_global=0 sw_stat_mismatch={mismatch}"
    )
    devices = [card.replace(" ", f"{i} ", 1) for i in range(branches) for card in cards]
    # Source the circuit after setting its seed. The PDK draws mismatch at elaboration.
    control = f"""Seeded GF180D open-switch control
.control
set numdgt=12
setseed {seed}
source dut.cir
op
let dc_a = i(vsense)
print dc_a
ac lin 1 10k 10k
let real_a = -real(i(vsense))
let imag_a = -imag(i(vsense))
print real_a imag_a
quit
.endc
.end
"""
    with tempfile.TemporaryDirectory() as directory:
        scratch = Path(directory)
        (scratch / "pdk").symlink_to(pdk)
        (scratch / "dut.cir").write_text("\n".join([base, *devices, ".end", ""]))
        (scratch / "job.cir").write_text(control)
        run = subprocess.run(
            [simulator, "-n", "-b", "job.cir"],
            cwd=scratch,
            capture_output=True,
            text=True,
            check=True,
        )
    values = dict(
        re.findall(r"(?m)^(dc_a|real_a|imag_a)\s*=\s*([-+\d.eE]+)$", run.stdout)
    )
    if len(values) != 3 or not all(isfinite(float(v)) for v in values.values()):
        raise ValueError(f"Incomplete {case}/{seed}: {run.stderr}")
    return dict(zip(COLUMNS[:5], (*case, seed)), **values)


def currents(row):
    return tuple(float(row[k]) for k in COLUMNS[5:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--output", type=Path, help="write the measured samples")
    args = parser.parse_args()
    if args.jobs < 1 or "ngspice-47" not in subprocess.check_output(
        [args.ngspice, "--version"], text=True
    ):
        parser.error("Use ngspice 47 and a positive worker count")
    pdk = args.pdk.resolve()
    check_inputs(pdk, include_pad=False)

    def sample(params):
        return measure(pdk, args.ngspice, *params)

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(
            pool.map(sample, ((case, seed) for case in CASES for seed in SEEDS))
        )

    n = len(SEEDS)
    # First order statistic with P[X_(k) >= q95] >= 0.95 for independent draws.
    rank = next(
        k
        for k in range(1, n + 1)
        if sum(comb(n, i) * 0.95**i * 0.05 ** (n - i) for i in range(k)) >= 0.95
    )
    for index, case in enumerate(CASES):
        group = rows[index * n : (index + 1) * n]
        repeat = measure(pdk, args.ngspice, case, SEEDS[0])
        if (
            currents(repeat) != currents(group[0])
            or len({currents(r) for r in group}) != n
        ):
            raise ValueError(f"Mismatch seeds or repeat failed at {case}")
        fixed = [
            currents(measure(pdk, args.ngspice, case, seed, mismatch=0))
            for seed in SEEDS[:2]
        ]
        if fixed[0] != fixed[1] or any(
            currents(measure(pdk, args.ngspice, case, SEEDS[0], branches=0))
        ):
            raise ValueError(f"Deterministic or disconnected control failed at {case}")
        dc = sorted(abs(currents(r)[0]) for r in group)
        ac = sorted(hypot(*currents(r)[1:]) for r in group)
        print(
            case,
            f"rank {rank}/{n}: DC {dc[rank - 1] * 1e12:.6f} pA, AC {ac[rank - 1] * 1e12:.6f} pA",
            f"(fixed {fixed[0][0] * 1e12:.6f} pA signed DC)",
        )
    if args.output:
        with args.output.open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    else:
        with (HERE / "mismatch.csv").open() as source:
            for reference, actual in zip(csv.DictReader(source), rows, strict=True):
                if any(str(actual[k]) != reference[k] for k in COLUMNS[:5]) or not all(
                    isclose(x, y, rel_tol=1e-6, abs_tol=1e-19)
                    for x, y in zip(currents(reference), currents(actual))
                ):
                    raise ValueError(f"Changed mismatch sample: {reference}")


if __name__ == "__main__":
    main()
