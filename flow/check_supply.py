"""Replay the macro supply ERC and open the two classes of physical tap contacts."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile

import klayout.db as db

MACRO = Path(__file__).resolve().parent / "readout"
TOP = "cryo_char_ctrl"


def run(stream, spec, missing_tie=None):
    result = subprocess.run(
        [
            "klt",
            "erc",
            str(stream),
            str(spec),
            "--top",
            TOP,
            "--deck",
            "gf180mcu",
            "--findings-only",
            "--compact",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
    )
    # KLT 0.9.2 also reports the antenna verdict. A findings-only run can
    # return 4 when antenna ratios were skipped even though it evaluated ERC.
    if result.returncode not in (0, 3, 4):
        raise RuntimeError(result.stderr or result.stdout)
    report = json.loads(result.stdout)
    if result.returncode == 4 and report["status"] != "not_checked":
        raise ValueError("Unexpected ERC process status")
    if report["provenance"]["klt_version"] != "0.9.2":
        raise ValueError("Use KLT 0.9.2 for the digital supply check")
    if {n["name"]: n["matched_islands"] for n in report["nets"]} != {
        "VDD": 1,
        "VSS": 1,
    }:
        raise ValueError("Expected one VDD and one VSS island")
    findings = [(f["rule"], f["layer"], f["net"]) for f in report["erc_findings"]]
    if missing_tie is None:
        if report["erc_status"] != "clean" or findings:
            raise ValueError(f"Supply ERC failed: {findings}")
    elif report["erc_status"] != "violations" or set(findings) != {
        ("erc.missing_tie", *missing_tie)
    }:
        raise ValueError(
            f"Opening {missing_tie} produced an unexpected result: {findings}"
        )
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--negative-control", action="store_true")
    args = p.parse_args()
    spec = MACRO / "erc.json"
    source = MACRO / f"{TOP}.gds"
    run(source, spec)
    if args.negative_control:
        layout = db.Layout()
        layout.read(str(source))
        top = layout.top_cell()
        top.flatten(-1, True)
        with tempfile.TemporaryDirectory() as tmp:
            stream = Path(tmp) / "control.gds"
            layout.write(str(stream))
            run(stream, spec)
            cuts = top.shapes(layout.find_layer(33, 0))
            original = db.Region(cuts).merged()
            active = db.Region(top.shapes(layout.find_layer(22, 0))).merged()
            nwell = db.Region(top.shapes(layout.find_layer(21, 0))).merged()
            pplus = db.Region(top.shapes(layout.find_layer(31, 0))).merged()
            nplus = db.Region(top.shapes(layout.find_layer(32, 0))).merged()
            for name, rail, footprint in (
                ("psub_vss", "VSS", (active & pplus) - nwell),
                ("nwell_vdd", "VDD", active & nplus & nwell),
            ):
                opened = original.inside(footprint)
                if opened.is_empty():
                    raise ValueError(f"No drawn contact cuts found for {name}")
                remaining = original - opened
                cuts.clear()
                cuts.insert(remaining)
                layout.write(str(stream))
                report = run(stream, spec, (name, rail))
                print(
                    f"Removing {opened.count()} {name} contacts produced "
                    f"{len(report['erc_findings'])} missing-tie findings on {rail}."
                )
    print("Readout VDD and VSS each form one island.")


if __name__ == "__main__":
    main()
