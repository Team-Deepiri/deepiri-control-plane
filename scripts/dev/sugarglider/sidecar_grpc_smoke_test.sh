#!/usr/bin/env bash
# Legacy alias: use sugar_glider_grpc_smoke_test.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/sugar_glider_grpc_smoke_test.sh" "$@"
