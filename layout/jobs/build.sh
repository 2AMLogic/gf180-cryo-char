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
ws_job_init "$out"

slot="$(ws_pin wafer_space.template.slot)"
scl="$(ws_pin wafer_space.template.scl)"
pad="$(ws_pin wafer_space.template.pad)"
sram="$(ws_pin wafer_space.template.sram)"
target="$(ws_pin wafer_space.template.target)"
make_vars=(SLOT="$slot" SCL="$scl" PAD="$pad" SRAM="$sram")

ws_bootstrap "$template" "${make_vars[@]}"

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

python3 "$LAYOUT_JOBS_HELPER" build "$out" "$gds" "$run_dir" "$target" "${probe:-0}" "${make_vars[@]}"
ws_phase "done: chip_top.gds $(sha256sum "$out/chip_top.gds" | cut -d' ' -f1)"
