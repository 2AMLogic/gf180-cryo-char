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
mkdir -p "$flow"
ws_job_init "$out"
harvest="$WS_OUT/flow"
ws_bootstrap "$precheck"

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
) >>"$WS_OUT/console.log" 2>&1
rc=$?
set -e

run_dir="$(find "$flow/runs" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -n 1)"
if [ -n "$run_dir" ]; then
	mkdir -p "$harvest"
	(cd "$run_dir" && find . -type f \( -name '*.json' -o -name '*.rpt' -o -name '*.log' -o -name '*.txt' \) \
		-size -8M -print0 | sort -z | xargs -0 -r cp --parents -t "$harvest/")
	(cd "$run_dir" && find . -type f -printf '%s\t%p\n' | sort -k2) >"$WS_OUT/flow-files.txt"
fi

python3 "$LAYOUT_JOBS_HELPER" precheck "$out" "$gds" "$rc" "$id" "$threads" "$workers" "${#cob[@]}" "$run_dir"
ws_phase "done: precheck exit $rc"
exit "$rc"
