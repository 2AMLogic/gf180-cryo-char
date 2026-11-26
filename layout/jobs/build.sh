#!/usr/bin/env bash
#
# Spot job: build the pinned wafer.space template to chip_top.gds (issue #4).
#
# Runs from the source root of the tarball layout/spot.py staged: this repo
# at one commit, and the template at its pinned commit under
# layout/vendor/template. Every Makefile variable is passed from
# layout/toolchain.json, so the build is upstream's own CI job and not
# whatever the Makefile defaults to on the day.
#
# Declared output, build/out/: chip_top.gds, build.json, console.log,
# tools.json, phases.txt and, when the flow wrote one, metrics.json. A GDS
# that is not produced is a failed shard (the runner exits 3 on a missing
# declared output), never a pass.
#
#   layout/jobs/build.sh [--probe]
#
# --probe stops after the bootstrap (Nix, PDK, tool record) and writes no GDS:
# it proves the environment in minutes, before the flow's hour is spent.
set -euo pipefail

probe=
if [ "${1:-}" = "--probe" ]; then
	probe=1
	shift
fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=nix-env.sh
. "$here/nix-env.sh"

out=build/out
template=layout/vendor/template
mkdir -p "$out"
WS_PHASES="$PWD/$out/phases.txt"
export WS_PHASES

finish() {
	local status=$?
	if [ "$status" -ne 0 ]; then
		ws_log "FAILED (exit $status); last 40 lines of the console log:"
		tail -n 40 "$out/console.log" >&2 2>/dev/null || true
	fi
}
trap finish EXIT

slot="$(ws_pin wafer_space.template.slot)"
scl="$(ws_pin wafer_space.template.scl)"
pad="$(ws_pin wafer_space.template.pad)"
sram="$(ws_pin wafer_space.template.sram)"
target="$(ws_pin wafer_space.template.target)"
make_vars=(SLOT="$slot" SCL="$scl" PAD="$pad" SRAM="$sram")
: >"$out/console.log"

ws_phase "install nix $(ws_pin nix.version)"
ws_nix_install

ws_phase "fetch the PDK (open_pdks $(ws_pin wafer_space.pdk.open_pdks_commit))"
(cd "$template" && ws_nix_develop . make clone-pdk "${make_vars[@]}") >>"$out/console.log" 2>&1

ws_phase "check the PDK revision"
ws_pdk_check "$template/gf180mcu" "$(ws_pin wafer_space.pdk.name)" \
	"$(ws_pin wafer_space.pdk.open_pdks_commit)" >>"$out/console.log" 2>&1

ws_phase "record the toolchain"
ws_nix_develop "$PWD/$template" bash "$here/nix-env.sh" tools >"$out/tools.json"

if [ -n "$probe" ]; then
	ws_phase "probe: stopping before the flow"
	printf 'probe: no flow was run\n' >"$out/chip_top.gds"
	gds="$out/chip_top.gds"
	run_dir="$out"
else
	ws_phase "make $target ${make_vars[*]}"
	(cd "$template" && ws_nix_develop . make "$target" "${make_vars[@]}") >>"$out/console.log" 2>&1
	gds="$template/final/gds/chip_top.gds"
	if [ ! -s "$gds" ]; then
		ws_log "FATAL: make $target succeeded without producing $gds"
		exit 1
	fi
	cp "$gds" "$out/chip_top.gds"
	run_dir="$(find "$template/librelane/runs" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
	if [ -f "$run_dir/final/metrics.json" ]; then
		cp "$run_dir/final/metrics.json" "$out/metrics.json"
	fi
fi

python3 - "$out" "$gds" "$run_dir" "$target" "${probe:-0}" "${make_vars[@]}" <<'PY'
import datetime
import hashlib
import json
import os
import socket
import sys
import time

out, gds, run_dir, target, probe, *make_vars = sys.argv[1:]
PROBE = probe == "1"
pinned = json.load(open(os.path.join("layout", "toolchain.json")))


def digest(path):
    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


phases = {}
for line in open(os.path.join(out, "phases.txt")):
    _, stamp, name = line.split(" ", 2)
    phases[name.strip()] = int(stamp)
ordered = sorted(phases.items(), key=lambda item: item[1])
wall = {ordered[i][0]: ordered[i + 1][1] - ordered[i][1] for i in range(len(ordered) - 1)}
if ordered:
    wall[ordered[-1][0]] = int(time.time()) - ordered[-1][1]

metrics = None
if os.path.isfile(os.path.join(out, "metrics.json")):
    metrics = json.load(open(os.path.join(out, "metrics.json")))

try:
    image = json.load(open("/etc/eda-batch-image.json"))
except (OSError, ValueError):
    image = None

sources = open("layout/vendor/template/gf180mcu/gf180mcuD/SOURCES").read().splitlines()
record = {
    "pass": not PROBE,
    "probe": PROBE,
    "template_commit": pinned["wafer_space"]["template"]["commit"],
    "target": target,
    "make": dict(argument.split("=", 1) for argument in make_vars),
    "run_tag": os.path.basename(run_dir.rstrip("/")),
    "gds": {"name": "chip_top.gds", "sha256": digest(os.path.join(out, "chip_top.gds")),
            "bytes": os.path.getsize(os.path.join(out, "chip_top.gds"))},
    "pdk": {"name": pinned["wafer_space"]["pdk"]["name"],
            "open_pdks_commit_observed": [line for line in sources if line.startswith("open_pdks")],
            "source_gds_sha256": digest(gds)},
    "tools": json.load(open(os.path.join(out, "tools.json"))),
    "metrics": metrics,
    "wall_seconds": wall,
    "host": socket.gethostname(),
    "image": image,
}
json.dump(record, open(os.path.join(out, "build.json"), "w"), indent=2, sort_keys=True)
print(datetime.datetime.now(datetime.timezone.utc).isoformat(), "build.json written")
PY
ws_phase "done: chip_top.gds $(sha256sum "$out/chip_top.gds" | cut -d' ' -f1)"
