#!/usr/bin/env bash
#
# Run the pinned wafer.space precheck on one GDS, on the Spot batch fleet
# (issue #4). The heavy run never executes here; see layout/README.md.
#
#   layout/precheck/run.sh check
#   layout/precheck/run.sh submit --gds FILE --label NAME [--cob] [--id HEX8]
#                                       [--threads N] [--workers N]
#   layout/precheck/run.sh collect GROUP [--wait SECONDS]
#   layout/precheck/run.sh record SHARD_DIR [--is-die]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec python3 -m layout.spot precheck "$@"
