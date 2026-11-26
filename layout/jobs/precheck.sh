#!/usr/bin/env bash
#
# Spot job: run the pinned wafer.space precheck on one GDS (issue #4).
#
# usage, from the source root:
#   layout/jobs/precheck.sh GDS OUTDIR [--cob] [--id HEX8] [--threads N] [--workers N]
#
# GDS is a path inside the job tree and OUTDIR (precheck/out) is the declared
# output. The flow runs from the pinned precheck tree, in that tree's own
# flake dev shell, against the PDK revision its Makefile pins: the way
# wafer.space's own CI runs it. precheck.py's exit code is the verdict; 0
# means every checker in its flow passed.
#
# Declared output, OUTDIR: precheck.json (verdict, options, tool record,
# metrics), console.log (the whole flow), tools.json, phases.txt and flow/
# (the run directory's reports, metrics and logs).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=nix-env.sh
. "$here/nix-env.sh"

if [ $# -lt 2 ]; then
	ws_log "usage: $0 GDS OUTDIR [--cob] [--id HEX8] [--threads N] [--workers N]"
	exit 2
fi
gds="$(readlink -f "$1")"
out="$2"
shift 2
if [ ! -s "$gds" ]; then
	ws_log "FATAL: no GDS at $gds"
	exit 2
fi
cob=()
id=FFFFFFFF
threads=2
workers=""
while [ $# -gt 0 ]; do
	case "$1" in
		--cob) cob=(--cob) ;;
		--id | --threads | --workers)
			[ $# -ge 2 ] || { ws_log "FATAL: $1 needs a value"; exit 2; }
			case "$1" in
				--id) id="$2" ;;
				--threads) threads="$2" ;;
				--workers) workers="$2" ;;
			esac
			shift ;;
		*) ws_log "FATAL: unknown argument: $1"; exit 2 ;;
	esac
	shift
done

precheck=layout/vendor/precheck
pdk_root="$PWD/$precheck/gf180mcu"
flow="$PWD/precheck/flow"
harvest="$PWD/$out/flow"
mkdir -p "$out" "$flow"
WS_PHASES="$PWD/$out/phases.txt"
export WS_PHASES

# shellcheck disable=SC2317
finish() {
	local status=$?
	if [ "$status" -ne 0 ]; then
		ws_log "FAILED (exit $status); last 40 lines of the console log:"
		tail -n 40 "$out/console.log" >&2 2>/dev/null || true
	fi
}
trap finish EXIT

: >"$out/console.log"

ws_phase "install nix $(ws_pin nix.version)"
ws_nix_install

ws_phase "fetch the PDK (open_pdks $(ws_pin wafer_space.pdk.open_pdks_commit))"
(cd "$precheck" && ws_nix_develop . make clone-pdk) >>"$out/console.log" 2>&1

ws_phase "check the PDK revision"
ws_pdk_check "$pdk_root" "$(ws_pin wafer_space.pdk.name)" \
	"$(ws_pin wafer_space.pdk.open_pdks_commit)" >>"$out/console.log" 2>&1

ws_phase "record the toolchain"
ws_nix_develop "$PWD/$precheck" bash "$here/nix-env.sh" tools >"$out/tools.json"

if [ -z "$workers" ]; then
	cores="$(nproc)"
	mem_kib="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
	by_cores=$((cores / threads))
	by_mem=$((mem_kib / 1024 / 1024 / 6))
	workers=$((by_cores < by_mem ? by_cores : by_mem))
	[ "$workers" -ge 1 ] || workers=1
	[ "$workers" -le 8 ] || workers=8
fi

ws_phase "precheck $(basename "$gds") id=$id threads=$threads workers=$workers cob=${#cob[@]}"
set +e
(
	cd "$precheck" && ws_nix_develop . env "PDK_ROOT=$pdk_root" PDK=gf180mcuD \
		python3 precheck.py --input "$gds" --top "$(ws_pin die.top)" --dir "$flow" \
		--slot "$(ws_pin die.slot)" --id "$id" --threads "$threads" --workers "$workers" "${cob[@]}"
) >>"$out/console.log" 2>&1
rc=$?
set -e

run_dir="$(find "$flow/runs" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -n 1)"
if [ -n "$run_dir" ]; then
	mkdir -p "$harvest"
	(cd "$run_dir" && find . -type f \( -name '*.json' -o -name '*.rpt' -o -name '*.log' -o -name '*.txt' \) \
		-size -8M -print0 | sort -z | xargs -0 -r cp --parents -t "$harvest/")
	(cd "$run_dir" && find . -type f -printf '%s\t%p\n' | sort -k2) >"$out/flow-files.txt"
fi

python3 - "$out" "$gds" "$rc" "$id" "$threads" "$workers" "${#cob[@]}" "$run_dir" <<'PY'
import datetime
import hashlib
import json
import os
import socket
import sys
import time

out, gds, rc, die_id, threads, workers, cob, run_dir = sys.argv[1:]
rc = int(rc)
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

metrics_path = ""
if run_dir:
    for candidate in ("final/metrics.json", "metrics.json"):
        if os.path.isfile(os.path.join(run_dir, candidate)):
            metrics_path = os.path.join(run_dir, candidate)
            break
metrics = json.load(open(metrics_path)) if metrics_path else None

try:
    image = json.load(open("/etc/eda-batch-image.json"))
except (OSError, ValueError):
    image = None

sources = open(os.path.join("layout", "vendor", "precheck", "gf180mcu", "gf180mcuD", "SOURCES")).read().splitlines()
record = {
    "pass": rc == 0,
    "exit_code": rc,
    "input": {"name": os.path.basename(gds), "sha256": digest(gds), "bytes": os.path.getsize(gds)},
    "options": {"top": pinned["die"]["top"], "slot": pinned["die"]["slot"], "id": die_id,
                "cob": cob == "1", "threads": int(threads), "workers": workers},
    "pins": {"precheck_commit": pinned["wafer_space"]["precheck"]["commit"],
             "pdk": pinned["wafer_space"]["pdk"]},
    "run_tag": os.path.basename(run_dir.rstrip("/")) if run_dir else None,
    "metrics": metrics,
    "tools": json.load(open(os.path.join(out, "tools.json"))),
    "pdk_open_pdks_observed": [line for line in sources if line.startswith("open_pdks")],
    "wall_seconds": wall,
    "host": socket.gethostname(),
    "image": image,
}
json.dump(record, open(os.path.join(out, "precheck.json"), "w"), indent=2, sort_keys=True)
print(datetime.datetime.now(datetime.timezone.utc).isoformat(), f"precheck exit {rc}")
PY
ws_phase "done: precheck exit $rc"
exit "$rc"
