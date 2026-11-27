#!/usr/bin/env bash
#
# Build the pinned wafer.space template to chip_top.gds on the Spot batch
# fleet (issue #4). The heavy run never executes here; see layout/README.md.
#
#   layout/build.sh check
#   layout/build.sh submit [--group ID] [--wait SECONDS]
#   layout/build.sh collect GROUP [--wait SECONDS]
#   layout/build.sh record SHARD_DIR [--as-die]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec python3 -m layout.spot build "$@"
