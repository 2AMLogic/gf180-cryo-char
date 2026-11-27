#!/usr/bin/env python3
"""Standalone pin, toolchain and summary-record helper for layout/jobs/ (issue #4).

Invoked via ``python3 layout/jobs/summary.py <subcommand> ...`` inside a Spot
``repo-script`` shard using only the Python stdlib and files under ``layout/``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.metadata
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

LAYOUT_DIR = Path(__file__).resolve().parents[1]
BATCH_IMAGE_JSON = Path("/etc/eda-batch-image.json")
TOOL_PROBES = (
    ("nix", ["nix", "--version"]),
    ("python", ["python3", "--version"]),
    ("klayout", ["klayout", "-v"]),
    ("magic", ["magic", "--version"]),
    ("yosys", ["yosys", "-V"]),
    ("openroad", ["openroad", "-version"]),
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def first_json(*paths: Path):
    for path in paths:
        if path.is_file():
            return load_json(path)
    return None


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def gds_descriptor(path: Path) -> dict:
    return {"name": path.name, "sha256": digest(path), "bytes": path.stat().st_size}


def wall_seconds(out: Path) -> dict[str, int]:
    phases = {
        name.strip(): int(stamp)
        for line in (out / "phases.txt").read_text(encoding="utf-8").splitlines()
        for _, stamp, name in [line.split(" ", 2)]
    }
    ordered = sorted(phases.items(), key=lambda item: item[1])
    wall = {
        ordered[i][0]: ordered[i + 1][1] - ordered[i][1]
        for i in range(len(ordered) - 1)
    }
    if ordered:
        wall[ordered[-1][0]] = int(time.time()) - ordered[-1][1]
    return wall


def batch_image():
    try:
        return load_json(BATCH_IMAGE_JSON)
    except (OSError, ValueError):
        return None


def observed_open_pdks(upstream: str, pdk_name: str) -> list[str]:
    sources = LAYOUT_DIR / "vendor" / upstream / "gf180mcu" / pdk_name / "SOURCES"
    return [
        line
        for line in sources.read_text(encoding="utf-8").splitlines()
        if line.startswith("open_pdks")
    ]


def write_summary(out: Path, filename: str, fields: dict, message: str) -> None:
    record = {
        **fields,
        "tools": load_json(out / "tools.json"),
        "wall_seconds": wall_seconds(out),
        "host": socket.gethostname(),
        "image": batch_image(),
    }
    (out / filename).write_text(
        json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(dt.datetime.now(dt.UTC).isoformat(), message)


def cmd_pin(dotted_key: str) -> None:
    node = load_json(LAYOUT_DIR / "toolchain.json")
    for key in dotted_key.split("."):
        node = node[key]
    print(node)


def cmd_tools() -> None:
    def probe(command: list[str]) -> str:
        try:
            out = subprocess.run(
                command, capture_output=True, text=True, timeout=300, check=False
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return f"unavailable: {exc}"
        lines = (out.stdout or out.stderr).strip().splitlines()
        return lines[0] if lines else f"no output (exit {out.returncode})"

    tools: dict = {name: probe(cmd) for name, cmd in TOOL_PROBES}
    try:
        tools["librelane"] = importlib.metadata.version("librelane")
    except importlib.metadata.PackageNotFoundError:
        tools["librelane"] = "unavailable: no librelane distribution in this python"
    tools["paths"] = {name: shutil.which(name) for name, _ in TOOL_PROBES[2:]}
    print(json.dumps(tools, indent=2, sort_keys=True))


def cmd_build(argv: list[str]) -> None:
    out_arg, gds_arg, run_dir, target, probe_arg, *make_vars = argv
    out = Path(out_arg)
    is_probe = probe_arg == "1"
    pinned = load_json(LAYOUT_DIR / "toolchain.json")
    pdk_name = pinned["wafer_space"]["pdk"]["name"]
    write_summary(
        out,
        "build.json",
        {
            "pass": not is_probe,
            "probe": is_probe,
            "template_commit": pinned["wafer_space"]["template"]["commit"],
            "target": target,
            "make": dict(argument.split("=", 1) for argument in make_vars),
            "run_tag": os.path.basename(run_dir.rstrip("/")),
            "gds": gds_descriptor(out / "chip_top.gds"),
            "pdk": {
                "name": pdk_name,
                "open_pdks_commit_observed": observed_open_pdks("template", pdk_name),
                "source_gds_sha256": digest(Path(gds_arg)),
            },
            "metrics": first_json(out / "metrics.json"),
        },
        "build.json written",
    )


def cmd_precheck(argv: list[str]) -> None:
    out_arg, gds_arg, rc_arg, die_id, threads, workers, cob, run_dir = argv
    out, rc = Path(out_arg), int(rc_arg)
    pinned = load_json(LAYOUT_DIR / "toolchain.json")
    pdk_name = pinned["wafer_space"]["pdk"]["name"]
    metrics_candidates = (
        (Path(run_dir) / "final/metrics.json", Path(run_dir) / "metrics.json")
        if run_dir
        else ()
    )
    write_summary(
        out,
        "precheck.json",
        {
            "pass": rc == 0,
            "exit_code": rc,
            "input": gds_descriptor(Path(gds_arg)),
            "options": {
                "top": pinned["die"]["top"],
                "slot": pinned["die"]["slot"],
                "id": die_id,
                "cob": cob == "1",
                "threads": int(threads),
                "workers": workers,
            },
            "pins": {
                "precheck_commit": pinned["wafer_space"]["precheck"]["commit"],
                "pdk": pinned["wafer_space"]["pdk"],
            },
            "run_tag": os.path.basename(run_dir.rstrip("/")) if run_dir else None,
            "metrics": first_json(*metrics_candidates),
            "pdk_open_pdks_observed": observed_open_pdks("precheck", pdk_name),
        },
        f"precheck exit {rc}",
    )


def main(argv: list[str]) -> int:
    action, *rest = argv if argv else [""]
    if action == "pin" and len(rest) == 1:
        cmd_pin(rest[0])
    elif action == "tools" and not rest:
        cmd_tools()
    elif action == "build" and len(rest) >= 5:
        cmd_build(rest)
    elif action == "precheck" and len(rest) == 8:
        cmd_precheck(rest)
    else:
        raise SystemExit(
            f"usage: summary.py {{pin|tools|build|precheck}} ... ({argv!r})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
