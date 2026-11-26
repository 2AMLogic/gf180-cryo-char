# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14", "klayout-tools==0.9.2"]
# ///
"""Reproduce the oscillator receiver macro and check a physical short between its supplies."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import klayout.db as db

HERE = Path(__file__).resolve().parent
KLT = Path(sys.executable).with_name("klt")
GDS = HERE / "efuse_ls.gds"
REFERENCE = HERE / "efuse_ls.spice"
PEX = HERE / "efuse_ls.pex.spice"
PINS = ["in", "out", "vdd33", "vprog", "vss"]
UPSTREAM_GDS = "7657f02a2e9b0c291112b6f57b0bbc1004616666ffcf52f6b1a08c0e08e22a31"
UPSTREAM_SPICE = "48eb3a59f93d6fecd7b1bc5b5c0d471244785b8cbdd0e5ba3dd0f219bea82d52"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def upstream_views(checkout, scratch):
    layout_path = checkout / "layout/efuse_otp_array.gds"
    source_path = checkout / "design/efuse_otp_array.spice"
    if sha(layout_path) != UPSTREAM_GDS or sha(source_path) != UPSTREAM_SPICE:
        raise ValueError(
            "The eFuse checkout differs from the two pinned source artifacts"
        )
    layout = db.Layout()
    layout.read(str(layout_path))
    options = db.SaveLayoutOptions()
    options.select_cell(layout.cell("efuse_ls").cell_index())
    options.gds2_write_timestamps = False
    stream = scratch / "cell.gds"
    layout.write(str(stream), options)
    subckt = re.search(
        r"^\.subckt efuse_ls\b.*?^\.ends[^\n]*",
        source_path.read_text(),
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if (
        sha(stream) != sha(GDS)
        or not subckt
        or subckt.group() + "\n" != REFERENCE.read_text()
    ):
        raise ValueError(
            "The receiver GDS or schematic differs from the upstream macro"
        )
    print("The isolated GDS and schematic match the pinned eFuse source.")


def device_topology(report):
    # Compare each body connection and the drawn gate dimensions in addition
    # to KLT's netlist comparison. The deck treats source/drain as symmetric.
    expected = Counter()
    for line in REFERENCE.read_text().splitlines():
        if not line.startswith("X"):
            continue
        _, drain, gate, source, body, model, *params = line.lower().split()
        dimensions = dict(p.split("=", 1) for p in params if p.startswith(("l=", "w=")))
        expected[
            (
                model.split("_")[0],
                gate,
                tuple(sorted((drain, source))),
                body,
                float(dimensions["l"].removesuffix("u")),
                float(dimensions["w"].removesuffix("u")),
            )
        ] += 1
    actual = Counter()
    for device in report["devices"]:
        n, p = device["nets"], device["params"]
        actual[
            (
                device["class"],
                n["g"],
                tuple(sorted((n["s"], n["d"]))),
                n["b"],
                p["l_um"],
                p["w_um"],
            )
        ] += 1
    if sum(expected.values()) != 6 or actual != expected:
        raise ValueError(
            f"Device connectivity or dimensions differ: {actual - expected}; {expected - actual}"
        )


def compare(stream, expected):
    request = json.loads((HERE / "lvs.json").read_text())
    request["layout"]["file"] = str(stream)
    result = subprocess.run(
        [KLT, "lvs", "-", "--format", "json"],
        cwd=HERE,
        input=json.dumps(request),
        text=True,
        capture_output=True,
    )
    if result.returncode not in (0, 3):
        raise RuntimeError(result.stderr or result.stdout)
    report = json.loads(result.stdout)
    if report["status"] != expected:
        raise ValueError(f"Expected {expected}, got {report['status']} on {stream}")
    if expected == "match":
        for kind, count in (("pins", 5), ("nets", 7), ("devices", 6)):
            if set(report["counts"][kind].values()) != {count}:
                raise ValueError(f"Incomplete {kind} correspondence on {stream}")
    return report


def supply_bridge(scratch):
    layout = db.Layout()
    layout.read(str(GDS))
    top = layout.top_cell()
    ports = {
        s.text.string: s.text.trans.disp
        for s in top.shapes(layout.layer(34, 10)).each()
        if s.is_text()
    }
    a, b = sorted((ports["vdd33"], ports["vprog"]), key=lambda p: p.x)
    top_metal = top.shapes(layout.layer(46, 0))
    if not db.Region(top.begin_shapes_rec(layout.layer(46, 0))).is_empty():
        raise ValueError("The experimental bridge expects Metal4 to be unused")
    # Add two electrically separate M4 probe arms and verify the cell still
    # matches. Closing their 1 um gap is the only change in the shorted case.
    y = max(a.y, b.y) + 1000
    mid = (a.x + b.x) // 2
    for point, end in ((a, mid - 500), (b, mid + 500)):
        for layer, half in (
            (34, 250),
            (35, 130),
            (36, 250),
            (38, 130),
            (42, 250),
            (40, 130),
            (46, 250),
        ):
            top.shapes(layout.layer(layer, 0)).insert(
                db.Box(point.x - half, point.y - half, point.x + half, point.y + half)
            )
        top_metal.insert(db.Box(point.x - 200, point.y - 200, point.x + 200, y + 200))
        top_metal.insert(db.Box(min(point.x, end), y - 200, max(point.x, end), y + 200))
    probe = scratch / "probe.gds"
    layout.write(str(probe))
    compare(probe, "match")
    top_metal.insert(db.Box(mid - 550, y - 200, mid + 550, y + 200))
    layout.write(str(probe))
    fault = compare(probe, "mismatch")
    if fault["counts"]["nets"]["layout"] != 6:
        raise ValueError("The bridge did not merge exactly the two probed supply nets")
    print(
        "Separate supply probes match; joining them changes seven nets to six and fails LVS."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--efuse-checkout", type=Path, help="also reproduce both source views"
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        scratch = Path(temp)
        if args.efuse_checkout:
            upstream_views(args.efuse_checkout.resolve(), scratch)
        netlist = scratch / "receiver.spice"
        output = subprocess.run(
            [
                KLT,
                "extract",
                GDS.name,
                "--deck",
                "gf180mcu",
                "--top",
                "efuse_ls",
                "--pdk",
                "gf180mcuD",
                "--deck-option",
                "metal_top=11K",
                "--pins",
                ",".join(PINS),
                "--parasitics",
                "-o",
                netlist,
                "--format",
                "json",
            ],
            cwd=HERE,
            capture_output=True,
            text=True,
            check=True,
        )
        report = json.loads(output.stdout)
        if (report["status"], report["pin_count"], report["device_count"]) != (
            "extracted",
            5,
            6,
        ):
            raise ValueError("Incomplete level shifter extraction")
        device_topology(report)
        if netlist.read_bytes() != PEX.read_bytes():
            raise ValueError("The extracted SPICE differs from the simulated file")
        compare(GDS, "match")
        supply_bridge(scratch)
    print("All six receiver transistors, five ports and the extracted SPICE match.")


if __name__ == "__main__":
    main()
