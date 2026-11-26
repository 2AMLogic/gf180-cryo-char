"""Simulate one GF180 ring feeding its placed controller clock tree."""

import argparse
from pathlib import Path
import json
import re

import ring_clock

MACRO = Path(__file__).resolve().parents[2] / "flow/readout"
CROSSING = Path(__file__).resolve().parents[2] / "design/ro-crossing"
LIBRARY = "gf180mcu_fd_sc_mcu7t5v0"
FAMILIES = ("7t", "9t", "9t", "12t") * 2


def tree(port, clock_input="out"):
    layout = (MACRO / "cryo_char_ctrl.def").read_text()
    spef = (MACRO / "cryo_char_ctrl.spef").read_text()
    caps = {
        name.replace("\\", ""): float(cap)
        for name, cap in re.findall(r"^\*D_NET (\S+) (\S+)", spef, re.MULTILINE)
    }
    components = dict(
        re.findall(r"^\s*- (\S+) (gf180mcu_fd_sc_mcu7t5v0__\w+) ", layout, re.MULTILINE)
    )
    net_section = layout.split("\nNETS ")[1].split("\nEND NETS")[0]
    nets = {
        name: re.findall(r"\( (\S+) (\S+) \)", connections)
        for name, connections in re.findall(
            r"^    - (\S+) (.*?) \+ USE ", net_section, re.MULTILINE | re.DOTALL
        )
    }

    root = f"ro_clk[{port}]"
    trunk = f"clknet_0_ro_clk[{port}]"
    root_buffer = f"clkbuf_0_ro_clk[{port}]"
    if set(nets[root]) != {("PIN", root), (root_buffer, "I")}:
        raise ValueError(f"Unexpected root connectivity on {root}")
    buffer = LIBRARY + "__buf_4"
    leaves = [f"clkbuf_1_{i}__f_ro_clk[{port}]" for i in (0, 1)]
    if any(components[name] != buffer for name in [root_buffer] + leaves):
        raise ValueError("Clock-tree buffers differ from the receiver model")
    if set(nets[trunk]) != {(root_buffer, "Z"), *((name, "I") for name in leaves)}:
        raise ValueError(f"Unexpected trunk connectivity on {trunk}")

    lines = [
        f"XROOT {clock_input} trunk vc vc 0 0 {buffer}",
        f"CTRUNK trunk 0 {caps[trunk]}f",
    ]
    sinks = 0
    for i, name in enumerate(leaves):
        wire = f"clknet_1_{i}__leaf_ro_clk[{port}]"
        leaf = f"leaf{i}"
        lines += [
            f"XLEAF{i} trunk {leaf} vc vc 0 0 {buffer}",
            f"CLF{i} {leaf} 0 {caps[wire]}f",
        ]
        for instance, pin in nets[wire]:
            cell = components[instance]
            if (instance, pin) == (name, "Z"):
                continue
            if pin == "CLK" and cell == LIBRARY + "__dffrnq_1":
                d, q = ("d", "q") if sinks == 0 else ("0", f"q{sinks}")
                lines.append(f"XFF{sinks} {d} rst {leaf} {q} vc vc 0 0 {cell}")
                sinks += 1
            elif instance.startswith("clkload") and pin == "I":
                lines.append(f"X{instance} {leaf} open_{instance} vc vc 0 0 {cell}")
            else:
                raise ValueError(f"Unexpected clock leaf terminal {instance}/{pin}")
    if sinks != 12:
        raise ValueError(f"Expected twelve clocked divider registers on {root}")
    return caps[root], lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", type=int, choices=range(8))
    parser.add_argument("process", choices=("typical", "ff", "ss", "fs", "sf"))
    parser.add_argument("temperature", type=int)
    parser.add_argument("voltage", type=ring_clock.positive)
    parser.add_argument("--logic-supply", type=ring_clock.positive, required=True)
    parser.add_argument(
        "--crossing",
        choices=("direct", "schematic", "extracted"),
        default="direct",
        help="connect the ring directly or through the six-transistor efuse_ls macro",
    )
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument(
        "--extracted-ring",
        action="store_true",
        help="use the routed oscillator GDS extraction",
    )
    parser.add_argument(
        "--pdk-source", choices=("open_pdks", "wafer-space"), default="open_pdks"
    )
    parser.add_argument("--duration-ns", type=ring_clock.positive, default=950)
    parser.add_argument("--step-ns", type=ring_clock.positive, default=0.04)
    args = parser.parse_args()
    args.family = FAMILIES[args.port]
    args.disabled = False
    args.wire_ff = 0
    crossing = {
        "direct": None,
        "schematic": CROSSING / "efuse_ls.spice",
        "extracted": CROSSING / "efuse_ls.pex.spice",
    }[args.crossing]
    args.load_ff, cells = tree(args.port, "translated" if crossing else "out")
    result = ring_clock.simulate(args, args.pdk.resolve(), cells, crossing)
    result.update(port=args.port, family=args.family, wire_ff=args.load_ff)
    if args.extracted_ring:
        result["ring_view"] = "extracted"
    if crossing:
        result["crossing"] = args.crossing
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
