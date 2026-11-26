"""Generate and measure one GF180 gated-ring clock for the readout timing experiment."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

# structure-map.md selects two independent 9-track specimens.
FAMILIES = {
    "7t": ("gf180mcu_fd_sc_mcu7t5v0", [482]),
    "9t": ("gf180mcu_fd_sc_mcu9t5v0", [483, 484]),
    "12t": ("gf180mcu_osu_sc_gp12t3v3", [487]),
}
PIN_FILE = Path(__file__).with_name("ring_inputs.json")


def cell_path(lib):
    return Path("libs.ref") / lib / "spice" / (lib + ".spice")


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("expected a finite positive value")
    return number


def deck(args, pdk):
    lib, _ = FAMILIES[args.family]
    ctrl = FAMILIES["7t"][0]
    supply = "vv 0" if args.family == "12t" else "vv vv 0 0"
    model = pdk / "libs.tech/ngspice"
    sources = [lib]
    if args.logic_supply and ctrl != lib:
        sources.append(ctrl)
    lines = [
        "GF180D 143-stage gated ring and buffer",
        f'.include "{model}/design.ngspice"',
        f'.lib "{model}/sm141064.ngspice" {args.process}',
    ]
    lines.extend(f'.include "{pdk / cell_path(source)}"' for source in sources)
    enable = 0 if args.disabled else args.voltage
    lines += [
        ".param sw_stat_global=0",
        f".temp {args.temperature}",
        f"VRO vv 0 {args.voltage}",
        f"VEN en 0 PWL(0 0 10n 0 10.2n {enable})",
        f"XG n142 en n0 {supply} {lib}__nand2_1",
    ]
    for i in range(1, 143):
        lines.append(f"X{i} n{i - 1} n{i} {supply} {lib}__inv_1")
    if args.wire_ff:
        lines.extend(f"CW{i} n{i} 0 {args.wire_ff}f" for i in range(143))
    if args.logic_supply:
        # Clock input has twelve DFFs in the routed DEF. Observe one as a toggle.
        logic = args.logic_supply
        lines += [
            f"VCTRL vc 0 {logic}",
            f"VRST rst 0 PWL(0 0 4n 0 4.1n {logic})",
            f"XINV q d vc vc 0 0 {ctrl}__inv_1",
            f"XFF d rst out q vc vc 0 0 {ctrl}__dffrnq_1",
        ]
        lines.extend(
            f"XLOAD{i} 0 rst out q{i} vc vc 0 0 {ctrl}__dffrnq_1" for i in range(1, 12)
        )
    probe = "q" if args.logic_supply else "n142"
    lines += [
        f"XB n142 out {supply} {lib}__buf_1",
        f"CL out 0 {args.load_ff}f",
        ".options num_threads=1",
        ".control",
        "set wr_singlescale",
        "set numdgt=10",
        f"tran {args.step_ns}n {args.duration_ns}n",
        f"wrdata wave.dat v(out) v({probe}) i(VRO)",
        "quit",
        ".endc",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def crossings(rows, column, threshold, rising_only):
    edges = []
    for a, b in zip(rows, rows[1:]):
        if a[column] < threshold <= b[column] or (
            not rising_only and b[column] < threshold <= a[column]
        ):
            edges.append(
                a[0] + (b[0] - a[0]) * (threshold - a[column]) / (b[column] - a[column])
            )
    return edges


def measure(rows, args):
    if not rows or any(len(r) != 4 or not all(map(math.isfinite, r)) for r in rows):
        raise ValueError("missing or non-finite transient samples")
    if rows[-1][0] < args.duration_ns * 1e-9 * 0.99999 or any(
        b[0] <= a[0] for a, b in zip(rows, rows[1:])
    ):
        raise ValueError("incomplete transient or invalid time axis")
    edges = [t for t in crossings(rows, 1, args.voltage / 2, True) if t > 10.2e-9]
    result = {"rising_edges": len(edges)}
    if args.disabled:
        if (
            edges
            or max(x[1] for x in rows) - min(x[1] for x in rows) > args.voltage * 0.05
        ):
            raise ValueError("disabled ring switched")
        return result
    if len(edges) < 4:
        raise ValueError(
            f"observed {len(edges)} edges after enable; increase --duration-ns"
        )
    # Drop the first start-up cycle. Integrate only complete subsequent cycles.
    start, end = edges[1], edges[-1]
    cycles = list(zip(edges[1:-1], edges[2:]))
    charge = 0
    for a, b in zip(rows, rows[1:]):
        left, right = max(a[0], start), min(b[0], end)
        if left < right:
            current = a[3] + (b[3] - a[3]) * ((left + right) / 2 - a[0]) / (b[0] - a[0])
            charge -= current * (right - left)
    window = [r for r in rows if start <= r[0] <= end]
    result.update(
        period_min_ns=min(b - a for a, b in cycles) * 1e9,
        period_max_ns=max(b - a for a, b in cycles) * 1e9,
        frequency_mhz=len(cycles) / (end - start) * 1e-6,
        average_vro_current_ua=charge / (end - start) * 1e6,
        output_low_v=min(r[1] for r in window),
        output_high_v=max(r[1] for r in window),
    )
    if args.logic_supply:
        transitions = crossings(rows, 2, args.logic_supply / 2, False)
        result["capture_windows"] = len(cycles)
        result["windows_with_one_toggle"] = sum(
            sum(a <= t < b for t in transitions) == 1 for a, b in cycles
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=FAMILIES)
    parser.add_argument("process", choices=["typical", "ff", "ss", "fs", "sf"])
    parser.add_argument("temperature", type=int, help="degrees C")
    parser.add_argument(
        "voltage", type=positive, help="ring and output buffer supply in volts"
    )
    parser.add_argument(
        "--pdk",
        type=Path,
        required=True,
        help="pinned open_pdks GF180D variant directory",
    )
    parser.add_argument(
        "--pdk-source",
        choices=("open_pdks", "wafer-space"),
        default="open_pdks",
        help="check model files against this PDK distribution",
    )
    parser.add_argument(
        "--logic-supply",
        type=positive,
        help="attach the twelve 7-track DFF clock inputs",
    )
    parser.add_argument(
        "--load-ff", type=positive, default=72, help="lumped output capacitance in fF"
    )
    parser.add_argument(
        "--wire-ff",
        type=positive,
        default=0,
        help="added internal capacitance per stage",
    )
    parser.add_argument("--step-ns", type=positive, default=0.12)
    parser.add_argument("--duration-ns", type=positive, default=350)
    parser.add_argument("--disabled", action="store_true")
    args = parser.parse_args()
    pdk = args.pdk.resolve()
    sim = os.environ.get("NGSPICE", "ngspice")
    pins = json.loads(PIN_FILE.read_text())[args.pdk_source]
    if cell_path(FAMILIES[args.family][0]).as_posix() not in pins:
        parser.error(f"{args.pdk_source} does not supply the {args.family} library")
    for name, expected in pins.items():
        if hashlib.sha256((pdk / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Unexpected GF180 source {name}")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)
        (path / "ring.cir").write_text(deck(args, pdk))
        run = subprocess.run(
            [sim, "-b", "ring.cir"], cwd=path, capture_output=True, text=True
        )
        waveform = path / "wave.dat"
        if run.returncode or not waveform.is_file():
            raise RuntimeError((run.stdout + run.stderr)[-2400:])
        data = [
            tuple(map(float, line.split()))
            for line in waveform.read_text().splitlines()
        ]
    results = measure(data, args)
    results.update(
        pdk_source=args.pdk_source,
        nist_codes=FAMILIES[args.family][1],
        family=args.family,
        process=args.process,
        temperature_c=args.temperature,
        vro_v=args.voltage,
        load_ff=args.load_ff,
        per_stage_wire_ff=args.wire_ff,
        logic_supply_v=args.logic_supply,
    )
    print(json.dumps(results, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
