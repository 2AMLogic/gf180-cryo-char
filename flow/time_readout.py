"""Run both routed GF180D timing cases and bind each result to its physical inputs."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

MACRO = Path(__file__).resolve().parent / "readout"


def input_hashes(request):
    config = json.loads(request.read_text())
    files = [request, request.parent / config["def"], request.parent / config["spef"]]
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def record(request):
    klt = os.environ.get("KLT", "klt")
    hashes = input_hashes(request)
    result = subprocess.run(
        [klt, "sta", str(request), "--pdk", "gf180mcuD", "--format", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 3):
        raise RuntimeError(result.stderr or result.stdout)
    report = json.loads(result.stdout)
    if report.get("provenance", {}).get("klt_version") != "0.9.2" or not report.get(
        "corners"
    ):
        raise ValueError("Expected a completed KLT 0.9.2 STA run")
    if hashes != input_hashes(request):
        raise ValueError("Timing inputs changed during STA")
    report["timing_input_sha256"] = hashes
    with tempfile.NamedTemporaryFile(
        mode="w", dir=request.parent, delete=False
    ) as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write("\n")
    Path(output.name).replace(request.with_suffix(".report.json"))


if __name__ == "__main__":
    for filename in ("timing.json", "timing-stress.json"):
        record(MACRO / filename)
