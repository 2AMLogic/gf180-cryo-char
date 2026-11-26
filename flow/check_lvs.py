"""Replay the GF180D macro LVS, optionally recording it or exercising physical faults."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import klayout.db as db

MACRO = Path(__file__).resolve().parent / "readout"
REQUEST = MACRO / "lvs.json"
REPORT = MACRO / "lvs.report.json"


def inputs():
    config = json.loads(REQUEST.read_text())
    names = [
        config["layout"]["file"],
        config["layout"]["def_pins"],
        config["reference"]["netlist"],
        REQUEST.name,
    ]
    return {
        name: hashlib.sha256((MACRO / name).read_bytes()).hexdigest() for name in names
    }


def compare(request):
    result = subprocess.run(
        [os.environ.get("KLT", "klt"), "lvs", str(request), "--format", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 3):
        raise RuntimeError(result.stderr or result.stdout)
    report = json.loads(result.stdout)
    if report.get("provenance", {}).get("klt_version") != "0.9.2":
        raise ValueError("Expected a KLT 0.9.2 LVS report")
    return report


def verify(report):
    power = report["power_connectivity"]
    if (
        report["status"] != "match"
        or report["error_count"]
        or power["status"] != "match"
        or power["finding_count"]
    ):
        raise ValueError("The routed controller failed signal or supply LVS")
    if report["lvs_input_sha256"] != inputs():
        raise ValueError(
            "LVS inputs differ from the recorded GDS, DEF, as-built netlist or request"
        )
    if (
        set(power["power_pins"]) != {"VDD", "VSS"}
        or set(power["unchecked_expected_pins"]) != {"VNW", "VPW"}
        or power["instance_count"]
        != json.loads((MACRO / "route.json").read_text())["placed_components"]
    ):
        raise ValueError("Supply coverage differs from the recorded VDD/VSS check")


def fault_controls(directory):
    request = json.loads(REQUEST.read_text())
    for obj, key in (
        (request["layout"], "file"),
        (request["layout"], "def_pins"),
        (request["reference"], "netlist"),
    ):
        obj[key] = str(MACRO / obj[key])

    def reject(name, category, signal, power):
        path = directory / f"{name}.json"
        path.write_text(json.dumps(request))
        report = compare(path)
        findings = set(report["category_error_counts"])
        findings.update(f["category"] for f in report["power_connectivity"]["findings"])
        if (report["status"], report["power_connectivity"]["status"]) != (
            signal,
            power,
        ) or category not in findings:
            raise ValueError(f"{name} failed to produce {category}: {findings}")
        print(f"{name}: signal {signal}, supply {power}, detected {category}")

    layout = db.Layout()
    original = request["layout"]["file"]
    layout.read(original)
    top = layout.top_cell()
    pins = {
        s.text.string: s.text.trans.disp
        for s in top.shapes(layout.find_layer(36, 10)).each()
        if s.is_text()
    }
    a, b = pins["ro_clk[6]"], pins["ro_clk[2]"]
    if a.y != b.y or a.x >= b.x:
        raise ValueError("Expected adjacent north Metal2 test ports")
    top.shapes(layout.find_layer(36, 0)).insert(db.Box(a.x, a.y - 40, b.x, b.y + 40))
    bridged = directory / "bridged.gds"
    layout.write(str(bridged))
    request["layout"]["file"] = str(bridged)
    reject("short-two-ring-ports", "net.merged", "mismatch", "match")
    request["layout"]["file"] = original

    # Clock just the bit-zero DFF of divider 7 from its neighbor.
    netlist = Path(request["reference"]["netlist"])
    source = netlist.read_text()
    start = source.index(" _247_ (")
    end = source.index(");", start)
    cell = source[start:end]
    if cell.count(".CLK(clknet_1_0__leaf_ro_clk[7])") != 1:
        raise ValueError("Expected the bit-zero divider 7 clock connection")
    changed = directory / "wrong-bank.v"
    changed.write_text(
        source[:start]
        + cell.replace(
            ".CLK(clknet_1_0__leaf_ro_clk[7])", ".CLK(clknet_1_0__leaf_ro_clk[6])"
        )
        + source[end:]
    )
    request["reference"]["netlist"] = str(changed)
    reject("wrong-divider-clock", "topology", "mismatch", "match")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--record", action="store_true", help="update the published LVS report"
    )
    p.add_argument(
        "--negative-controls",
        action="store_true",
        help="short two physical ports and miswire a reference clock in temporary files",
    )
    args = p.parse_args()
    before = inputs()
    report = compare(REQUEST)
    report["lvs_input_sha256"] = before
    verify(report)
    if args.negative_controls:
        with tempfile.TemporaryDirectory() as directory:
            fault_controls(Path(directory))
    if args.record:
        with tempfile.NamedTemporaryFile(mode="w", dir=MACRO, delete=False) as out:
            json.dump(report, out, indent=2, allow_nan=False)
            out.write("\n")
        Path(out.name).replace(REPORT)
    print("GF180D readout signal and supply connectivity match.")


if __name__ == "__main__":
    main()
