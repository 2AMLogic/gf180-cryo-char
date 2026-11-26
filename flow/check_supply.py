"""Replay the macro supply ERC and a layout with the substrate contacts removed."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile

import klayout.db as db

MACRO = Path(__file__).resolve().parent / "readout"
TOP = "cryo_char_ctrl"


def run(stream, spec, expect_clean):
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
    if result.returncode not in (0, 3):
        raise RuntimeError(result.stderr or result.stdout)
    report = json.loads(result.stdout)
    if report["provenance"]["klt_version"] != "0.9.2":
        raise ValueError("Use KLT 0.9.2 for the digital supply check")
    if {n["name"]: n["matched_islands"] for n in report["nets"]} != {
        "VDD": 1,
        "VSS": 1,
    }:
        raise ValueError("Expected one VDD and one VSS island")
    findings = [(f["rule"], f["layer"], f["net"]) for f in report["erc_findings"]]
    if expect_clean:
        if report["erc_status"] != "clean" or findings:
            raise ValueError(f"Supply ERC failed: {findings}")
    elif report["erc_status"] != "violations" or findings != [
        ("erc.missing_tie", "psub_vss", "VSS")
    ]:
        raise ValueError(
            f"Missing substrate taps produced an unexpected result: {findings}"
        )
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--negative-control", action="store_true")
    args = p.parse_args()
    spec = MACRO / "erc.json"
    source = MACRO / f"{TOP}.gds"
    run(source, spec, True)
    if args.negative_control:
        layout = db.Layout()
        layout.read(str(source))
        top = layout.top_cell()
        top.flatten(-1, True)
        with tempfile.TemporaryDirectory() as tmp:
            stream = Path(tmp) / "control.gds"
            layout.write(str(stream))
            run(stream, spec, True)
            implants = top.shapes(layout.find_layer(31, 0))
            all_pplus = db.Region(implants).merged()
            active = db.Region(top.shapes(layout.find_layer(22, 0))).merged()
            nwell = db.Region(top.shapes(layout.find_layer(21, 0))).merged()
            taps = (all_pplus & active) - nwell
            if taps.is_empty():
                raise ValueError("No substrate contacts to remove")
            remaining = all_pplus - taps
            implants.clear()
            implants.insert(remaining)
            layout.write(str(stream))
            run(stream, spec, False)
            print(
                f"Removing {taps.count()} substrate tap regions triggered the VSS missing-tie check."
            )
    print("Readout VDD and VSS each form one island.")


if __name__ == "__main__":
    main()
