#!/usr/bin/env bash
#
# Shared bootstrap for the layout/ Spot jobs (issue #4). Sourced by build.sh
# and precheck.sh inside a repo-script job on the heavy image; never run,
# except as `nix-env.sh tools` inside a dev shell, to print its tool record.
#
#   ws_pin KEY[.KEY...]         one value from layout/toolchain.json
#   ws_log MSG                  a timestamped progress line
#   ws_nix_install              install the sha256-pinned Nix, single-user
#   ws_nix_develop DIR CMD...   run CMD in the pinned flake's dev shell
#   ws_pdk_check ROOT VARIANT   fail unless ROOT/VARIANT/SOURCES names the
#                               pinned open_pdks commit
#   ws_phase MSG                append MSG to $WS_PHASES with its timestamp
#   ws_tools                    the dev shell's tool versions, as JSON
#
# The job instance has egress and no credential. It fetches exactly three
# things: the Nix tarball (hash-checked here), the flake closure from its
# binary caches, and the PDK from Ciel. The upstream sources arrive in the
# job tarball; nothing is cloned. Nix goes in single-user: there is no
# daemon to supervise and the instance is discarded when the job ends.
set -euo pipefail

LAYOUT_JOB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NIX_CONFIG="experimental-features = nix-command flakes"

ws_pin() {
	python3 - "$LAYOUT_JOB_DIR/toolchain.json" "$1" <<'PY'
import json, sys

node = json.load(open(sys.argv[1]))
for key in sys.argv[2].split("."):
	node = node[key]
print(node)
PY
}

ws_log() { echo "[layout-job $(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >&2; }

ws_phase() {
	echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) $*" >> "${WS_PHASES:-/dev/null}"
	ws_log "$*"
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
	python3 - <<'PY'
import importlib.metadata
import json
import shutil
import subprocess


def first(command):
    try:
        out = subprocess.run(command, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unavailable: {exc}"
    line = (out.stdout or out.stderr).strip().splitlines()
    return line[0] if line else f"no output (exit {out.returncode})"


tools = {
    "nix": first(["nix", "--version"]),
    "python": first(["python3", "--version"]),
    "klayout": first(["klayout", "-v"]),
    "magic": first(["magic", "--version"]),
    "yosys": first(["yosys", "-V"]),
    "openroad": first(["openroad", "-version"]),
}
try:
    tools["librelane"] = importlib.metadata.version("librelane")
except importlib.metadata.PackageNotFoundError:
    tools["librelane"] = "unavailable: no librelane distribution in this python"
tools["paths"] = {name: shutil.which(name) for name in ("klayout", "magic", "yosys", "openroad")}
print(json.dumps(tools, indent=2, sort_keys=True))
PY
}

if [ "${BASH_SOURCE[0]}" = "$0" ] && [ "${1:-}" = tools ]; then
	ws_tools
fi
