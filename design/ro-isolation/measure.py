"""Replay complete-cycle currents and readout captures on the physically isolated rings."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "sim/readout"))
import ring_clock  # noqa: E402
import routed_ring  # noqa: E402

PORTS = (0, 2, 3)
MODES = ("isolated", "unloaded", "read", "original")
INPUTS = ("port", "process", "temp", "vro", "logic", "mode", "step_ns", "duration_ns")
COUNTS = ("rising_edges", "capture_windows", "windows_with_one_toggle")


def points():
    for process, temp, vro, logic, step, duration in (
        ("ff", -40, 1.4, 3.6, 0.025, 950),
        ("ff", -40, 3.6, 3.6, 0.005, 160),
        ("typical", 25, 1.4, 3.3, 0.05, 1600),
        ("ss", 125, 1.4, 3, 0.06, 2200),
    ):
        for port in PORTS:
            for mode in MODES:
                yield port, process, temp, vro, logic, mode, step, duration
    # Bound the voltage dependence and repeat both endpoint differences at half step.
    for vro, step, duration in (
        (1.8, 0.015, 600),
        (2.6, 0.01, 360),
        (1.4, 0.0125, 950),
        (3.6, 0.0025, 160),
    ):
        for port in PORTS:
            for mode in ("isolated", "unloaded"):
                yield port, "ff", -40, vro, 3.6, mode, step, duration


def measure(point, pdk, ngspice):
    port, process, temp, vro, logic, mode, step, duration = point
    family = routed_ring.FAMILIES[port]
    name = "ro_" + family
    tree_load, tree = routed_ring.tree(port, "translated")
    library = routed_ring.LIBRARY
    lines = [
        "Extracted oscillator, isolation, and routed GF180D divider",
        f'.include "{pdk}/libs.tech/ngspice/design.ngspice"',
        f'.lib "{pdk}/libs.tech/ngspice/sm141064.ngspice" {process}',
        f'.include "{pdk / ring_clock.cell_path(library)}"',
        f'.include "{ROOT}/design/ro-crossing/efuse_ls.pex.spice"',
        ".param sw_stat_global=0",
        f".temp {temp}",
        f"VRO vv 0 {vro}",
        f"VCTRL vc 0 {logic}",
        f"VEN en 0 PWL(0 0 10n 0 10.2n {vro})",
        f"VRST rst 0 PWL(0 0 4n 0 4.1n {logic})",
        "VSHIFTLO vv shlo 0",
        "VSHIFTHI vc shhi 0",
    ]
    if mode in ("isolated", "read"):
        lines += [
            f'.include "{HERE}/{name}_read.pex.spice"',
            f"XRING en rx read readb vv 0 {name}_read",
            f"VREAD read 0 {logic if mode == 'read' else 0}",
            f"XINVB read readb vc vc 0 0 {library}__inv_1",
        ]
        raw, receiver = "xring.out", "rx"
    else:
        lines += [
            f'.include "{ROOT}/design/rings/{name}.pex.spice"',
            f"XRING en raw vv 0 {name}",
        ]
        raw, receiver = "raw", "raw" if mode == "original" else "0"
    lines.extend(
        [
            f"XSHIFT {receiver} translated shlo shhi 0 efuse_ls",
            f"XINV q d vc vc 0 0 {library}__inv_1",
            *tree,
            f"CL translated 0 {tree_load}f",
        ]
    )
    # ngspice does not export v(0). A grounded receiver has exactly zero
    # signal; retain the enable waveform as the unused final column.
    vectors = f"v({raw}) v(q) i(VRO) v(translated) i(VSHIFTLO) i(VSHIFTHI) v({receiver if receiver != '0' else 'en'})"
    lines.extend(
        [
            ".options num_threads=1",
            ".control",
            "set wr_singlescale",
            "set numdgt=10",
            f"save {vectors}",
            f"tran {step}n {duration}n",
            f"wrdata wave.dat {vectors}",
            "quit",
            ".endc",
            ".end",
        ]
    )
    with tempfile.TemporaryDirectory() as tempdir:
        work = Path(tempdir)
        (work / "d.cir").write_text("\n".join(lines) + "\n")
        run = subprocess.run(
            [ngspice, "-b", "d.cir"], cwd=work, capture_output=True, text=True
        )
        wave = work / "wave.dat"
        if run.returncode or not wave.exists():
            raise RuntimeError(run.stdout[-800:] + run.stderr[-1000:])
        rows = [
            tuple(map(float, line.split())) for line in wave.read_text().splitlines()
        ]
    args = SimpleNamespace(
        voltage=vro, logic_supply=logic, duration_ns=duration, disabled=False
    )
    if any(len(row) != 8 or not math.isfinite(row[7]) for row in rows):
        raise ValueError("Invalid receiver waveform")
    measured = ring_clock.measure([row[:7] for row in rows], args, True)
    edges = [t for t in ring_clock.crossings(rows, 1, vro / 2, True) if t > 10.2e-9]
    samples = (
        [r[7] for r in rows if edges[1] <= r[0] <= edges[-1]]
        if receiver != "0"
        else [0]
    )
    return {
        **dict(zip(INPUTS, point)),
        **measured,
        "rx_min": min(samples),
        "rx_max": max(samples),
    }


def current_errors(rows):
    by_point = {}
    for row in rows:
        key = tuple(
            float(row[k]) if k not in ("process", "mode") else row[k]
            for k in INPUTS
            if k != "mode"
        )
        current = float(row["average_vro_current_ua"])
        if row["mode"] == "unloaded":
            # The shifter input is tied low in this control. Remove its measured
            # quiescent draw to recover current in the bare oscillator alone.
            current -= float(row["shifter_ring_supply_ua"])
        by_point.setdefault(key, {})[row["mode"]] = current
    return {
        key: group["isolated"] - group["unloaded"] for key, group in by_point.items()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--port", type=int, choices=PORTS)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--output", type=Path, help="write fresh results to CSV")
    args = parser.parse_args()
    pdk = args.pdk.resolve()
    for path, digest in json.loads(ring_clock.PIN_FILE.read_text())[
        "open_pdks"
    ].items():
        if hashlib.sha256((pdk / path).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Unexpected PDK file {path}")
    ngspice = os.environ.get("NGSPICE", "ngspice")
    if "ngspice-46 " not in subprocess.check_output([ngspice, "--version"], text=True):
        parser.error("ngspice 46 is required")
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    selected = [
        point for point in points() if args.port is None or point[0] == args.port
    ]
    with ThreadPoolExecutor(args.jobs) as pool:
        rows = list(pool.map(lambda point: measure(point, pdk, ngspice), selected))
    if args.output:
        with args.output.open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=list(rows[0]), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        return
    with (HERE / "measurements.csv").open() as stream:
        expected = [
            r
            for r in csv.DictReader(stream)
            if args.port is None or int(r["port"]) == args.port
        ]
    if len(rows) != len(expected):
        raise ValueError("Measurement grid differs")
    for fresh, old in zip(rows, expected):
        for key, value in fresh.items():
            if key in ("process", "mode"):
                matches = value == old[key]
            elif key in INPUTS + COUNTS:
                matches = float(value) == float(old[key])
            else:
                matches = math.isclose(
                    value, float(old[key]), rel_tol=0.005, abs_tol=0.001
                )
            if not matches:
                raise ValueError(
                    f"{tuple(fresh[k] for k in INPUTS)} {key}: {old[key]} -> {value}"
                )
    # The resolution needed for a difference of two large currents is tighter
    # than their independent relative replay tolerances. Check the pair itself.
    old_errors = current_errors(expected)
    for key, error in current_errors(rows).items():
        if abs(error - old_errors[key]) > 0.01:
            raise ValueError(f"Added VRO current changed by over 0.010 µA at {key}")
    print(f"Reproduced {len(rows)} transients and their paired current differences.")


if __name__ == "__main__":
    main()
