"""Replay measured receiver points with one of the two pinned PDK distributions."""

import argparse
import csv
import json
import math
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
RUNNER = HERE.parents[1] / "sim/readout/routed_ring.py"


def check_analog(command, actual, reference, fields):
    for field in fields:
        if not math.isclose(
            actual[field], float(reference[field]), rel_tol=0.005, abs_tol=0.001
        ):
            raise ValueError(
                f"{command}: {field} changed from {reference[field]} to {actual[field]}"
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument(
        "--pdk-source", choices=("open_pdks", "wafer-space"), required=True
    )
    parser.add_argument(
        "--port", type=int, choices=range(8), help="limit replay to one port"
    )
    args = parser.parse_args()
    with (HERE / "measurements.csv").open() as stream:
        points = [
            r
            for r in csv.DictReader(stream)
            if r["pdk_source"] == args.pdk_source
            and (args.port is None or int(r["port"]) == args.port)
        ]
    if not points:
        parser.error("No measured points match this source and port")
    for r in points:
        command = [
            sys.executable,
            RUNNER,
            r["port"],
            r["process"],
            r["temperature_c"],
            r["vro_v"],
            "--logic-supply",
            r["logic_v"],
            "--step-ns",
            r["step_ns"],
            "--duration-ns",
            r["duration_ns"],
            "--pdk",
            args.pdk,
            "--pdk-source",
            args.pdk_source,
            "--crossing",
            r["crossing"],
        ]
        actual = json.loads(subprocess.check_output(command, text=True))
        for field in ("capture_windows", "windows_with_one_toggle"):
            if actual[field] != int(r[field]):
                raise ValueError(
                    f"{command}: {field} changed from {r[field]} to {actual[field]}"
                )
        check_analog(
            command,
            actual,
            r,
            (
                "frequency_mhz",
                "period_min_ns",
                "translated_low_v",
                "translated_high_v",
                "average_vro_current_ua",
                "shifter_ring_supply_ua",
                "shifter_controller_supply_ua",
            ),
        )
    print(f"Reproduced {len(points)} receiver measurements on {args.pdk_source}.")
    if args.pdk_source == "open_pdks":
        families = {point["family"] for point in points}
        with (HERE / "unloaded.csv").open() as stream:
            controls = [r for r in csv.DictReader(stream) if r["family"] in families]
        for r in controls:
            command = [
                sys.executable,
                RUNNER.with_name("ring_clock.py"),
                r["family"],
                r["process"],
                r["temperature_c"],
                r["vro_v"],
                "--pdk",
                args.pdk,
                "--step-ns",
                r["step_ns"],
                "--duration-ns",
                r["duration_ns"],
                "--load-ff",
                "0",
            ]
            actual = json.loads(subprocess.check_output(command, text=True))
            check_analog(
                command, actual, r, ("frequency_mhz", "average_vro_current_ua")
            )
        print(f"Reproduced {len(controls)} unloaded oscillator controls.")


if __name__ == "__main__":
    main()
