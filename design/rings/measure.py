"""Reproduce the extracted oscillator and receiver measurements with ngspice 46."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import math
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[1] / "sim/readout"
FAMILIES = ("7t", "9t", "9t", "12t") * 2
SETTINGS = (
    "port",
    "family",
    "process",
    "temperature_c",
    "vro_v",
    "logic_v",
    "step_ns",
    "duration_ns",
    "receiver",
)
READINGS = (
    "rising_edges",
    "capture_windows",
    "windows_with_one_toggle",
    "frequency_mhz",
    "period_min_ns",
    "average_vro_current_ua",
    "shifter_ring_supply_ua",
    "shifter_controller_supply_ua",
)


def cases():
    for port, family in enumerate(FAMILIES):
        yield (port, family, "ff", -40, 1.4, 3.6, 0.04, 950, "extracted")
        if port not in (0, 2, 3):
            continue
        yield (port, family, "typical", 25, 1.4, 3.3, 0.05, 1600, "extracted")
        yield (port, family, "ss", 125, 1.4, 3.0, 0.06, 2200, "extracted")
        yield (port, family, "ff", -40, 3.6, 3.6, 0.005, 125, "extracted")
        for process in ("typical", "ff", "ss", "fs", "sf"):
            for temperature in (-40, 25, 125):
                if (process, temperature) != ("ff", -40):
                    yield (
                        port,
                        family,
                        process,
                        temperature,
                        3.6,
                        3.6,
                        0.02,
                        260,
                        "extracted",
                    )
        yield (port, family, "ff", -40, 1.4, 3.6, 0.04, 950, "direct")
        yield (port, family, "ff", -40, 1.4, "", 0.04, 950, "unloaded")
        yield (port, family, "ff", -40, 1.4, "", 0.04, 200, "disabled")


def simulate(case, pdk):
    port, family, process, temp, vro, logic, step, duration, receiver = case
    if receiver in ("unloaded", "disabled"):
        args = [
            SIM / "ring_clock.py",
            family,
            process,
            str(temp),
            str(vro),
            "--load-ff",
            "0",
        ]
        if receiver == "disabled":
            args.append("--disabled")
    else:
        args = [
            SIM / "routed_ring.py",
            str(port),
            process,
            str(temp),
            str(vro),
            "--logic-supply",
            str(logic),
            "--crossing",
            receiver,
        ]
    args += [
        "--pdk",
        pdk,
        "--step-ns",
        str(step),
        "--duration-ns",
        str(duration),
        "--extracted-ring",
    ]
    result = json.loads(subprocess.check_output([sys.executable, *args], text=True))
    row = dict(zip(SETTINGS, case))
    row.update({key: result.get(key, "") for key in READINGS})
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--port", type=int, choices=range(8))
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--output", type=Path, help="write fresh readings to this CSV")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    if "ngspice-46 " not in subprocess.check_output(
        [os.environ.get("NGSPICE", "ngspice"), "--version"], text=True
    ):
        parser.error("the published measurements require ngspice 46")
    points = [case for case in cases() if args.port is None or args.port == case[0]]
    with ThreadPoolExecutor(args.jobs) as pool:
        rows = list(pool.map(lambda case: simulate(case, args.pdk.resolve()), points))
    if args.output:
        with args.output.open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=SETTINGS + READINGS, lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        return
    with (HERE / "measurements.csv").open() as stream:
        previous = [
            r
            for r in csv.DictReader(stream)
            if args.port is None or int(r["port"]) == args.port
        ]
    if len(rows) != len(previous):
        raise ValueError("Measurement grid changed")
    for row, old in zip(rows, previous):
        for key in SETTINGS + READINGS:
            value = row[key]
            if key in SETTINGS or key in READINGS[:3] or value == "":
                matches = str(value) == old[key]
            else:
                matches = math.isclose(
                    value, float(old[key]), rel_tol=0.005, abs_tol=0.001
                )
            if not matches:
                raise ValueError(
                    f"Port {row['port']} {row['receiver']} {key}: {old[key]} -> {value}"
                )
    print(f"Reproduced {len(rows)} extracted oscillator measurements.")


if __name__ == "__main__":
    main()
