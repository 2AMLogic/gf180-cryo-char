#!/usr/bin/env bash
#
# Shared bootstrap for the layout/ Spot jobs (issue #4). Sourced by build.sh
# and precheck.sh inside a repo-script job on the heavy image; never run,
# except as `nix-env.sh tools` inside a dev shell, to print its tool record.
#
#   ws_pin KEY[.KEY...]             one value from layout/toolchain.json
#   ws_log MSG                      a timestamped progress line
#   ws_phase MSG                    append MSG to $WS_PHASES with its timestamp
#   ws_job_init OUTDIR              create OUTDIR, arm the failure trap, reset console.log
#   ws_nix_install                  install the sha256-pinned Nix, single-user
#   ws_nix_develop DIR CMD...       run CMD in the pinned flake's dev shell
#   ws_pdk_check ROOT VARIANT SHA   fail unless ROOT/VARIANT/SOURCES names SHA
#   ws_tools                        the dev shell's tool versions, as JSON
#   ws_bootstrap UPSTREAM [MAKE...] install Nix, fetch/check PDK, write tools.json
#
# The job instance has egress and no credential. It fetches exactly three
# things: the Nix tarball (hash-checked here), the flake closure from its
# binary caches, and the PDK from Ciel. The upstream sources arrive in the
# job tarball; nothing is cloned. Nix goes in single-user: there is no
# daemon to supervise and the instance is discarded when the job ends.
set -euo pipefail

LAYOUT_JOB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAYOUT_JOBS_HELPER="$LAYOUT_JOB_DIR/jobs/summary.py"
# The job runs as root, and Nix as root insists on a build-users group unless
# the setting is emptied: the same nix.conf the official nixos/nix image ships.
export NIX_CONFIG="experimental-features = nix-command flakes
build-users-group ="

ws_pin() {
	python3 "$LAYOUT_JOBS_HELPER" pin "$1"
}

ws_log() { echo "[layout-job $(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >&2; }

ws_phase() {
	echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) $*" >> "${WS_PHASES:-/dev/null}"
	ws_log "$*"
}

# shellcheck disable=SC2317
_ws_finish() {
	local status=$?
	if [ "$status" -ne 0 ]; then
		ws_log "FAILED (exit $status); last 40 lines of the console log:"
		tail -n 40 "$WS_OUT/console.log" >&2 2>/dev/null || true
	fi
}

ws_job_init() {
	mkdir -p "$1"
	WS_OUT="$(cd "$1" && pwd)"
	WS_PHASES="$WS_OUT/phases.txt"
	export WS_OUT WS_PHASES
	: >"$WS_OUT/console.log"
	trap _ws_finish EXIT
}

ws_nix_install() {
	local version url sha work
	version="$(ws_pin nix.version)"
	if command -v nix >/dev/null 2>&1 && [ "$(nix --version | awk '{print $3}')" = "$version" ]; then
		ws_log "nix $version is already on PATH"
		return 0
	fi
	url="$(ws_pin nix.url)"
	sha="$(ws_pin nix.sha256)"
	work="$(mktemp -d "${TMPDIR:-/var/tmp}/nix-install.XXXXXX")"
	curl -fsSL --retry 5 --retry-delay 5 -o "$work/nix.tar.xz" "$url"
	if ! echo "$sha  $work/nix.tar.xz" | sha256sum -c - >/dev/null; then
		ws_log "FATAL: the Nix tarball from $url does not hash to the pinned $sha"
		return 1
	fi
	if command -v xz >/dev/null 2>&1; then
		tar -xJf "$work/nix.tar.xz" -C "$work"
	else
		python3 -m tarfile -e "$work/nix.tar.xz" "$work"
	fi
	"$work/nix-$version-x86_64-linux/install" --no-daemon --yes
	rm -rf "$work"
	export PATH="/nix/var/nix/profiles/default/bin:$PATH"
	export NIX_SSL_CERT_FILE="${NIX_SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
	if [ "$(nix --version | awk '{print $3}')" != "$version" ]; then
		ws_log "FATAL: nix --version does not report $version"
		return 1
	fi
}

ws_nix_develop() {
	local dir="$1"
	shift
	nix develop "$dir" --accept-flake-config --command "$@"
}

ws_pdk_check() {
	local sources="$1/$2/SOURCES" commit="$3"
	if [ ! -f "$sources" ]; then
		ws_log "FATAL: $sources is missing"
		return 1
	fi
	if ! grep -qE "^open_pdks[[:space:]]+$commit" "$sources"; then
		ws_log "FATAL: $sources does not pin open_pdks $commit:"
		cat "$sources" >&2
		return 1
	fi
	ws_log "$sources pins open_pdks $commit"
}

ws_tools() {
	python3 "$LAYOUT_JOBS_HELPER" tools
}

ws_bootstrap() {
	local upstream pdk_name pdk_commit
	upstream="$(cd "$1" && pwd)"
	shift
	pdk_name="$(ws_pin wafer_space.pdk.name)"
	pdk_commit="$(ws_pin wafer_space.pdk.open_pdks_commit)"

	ws_phase "install nix $(ws_pin nix.version)"
	ws_nix_install

	ws_phase "fetch the PDK (open_pdks $pdk_commit)"
	(cd "$upstream" && ws_nix_develop . make clone-pdk "$@") >>"$WS_OUT/console.log" 2>&1

	ws_phase "check the PDK revision"
	ws_pdk_check "$upstream/gf180mcu" "$pdk_name" "$pdk_commit" >>"$WS_OUT/console.log" 2>&1

	ws_phase "record the toolchain"
	ws_nix_develop "$upstream" bash "$LAYOUT_JOB_DIR/jobs/nix-env.sh" tools >"$WS_OUT/tools.json"
}

if [ "${BASH_SOURCE[0]}" = "$0" ] && [ "${1:-}" = tools ]; then
	ws_tools
fi
