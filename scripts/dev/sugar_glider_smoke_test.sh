#!/usr/bin/env bash
# Sugar Glider smoke test alias (legacy script: sidecar_smoke_test.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/sidecar_smoke_test.sh" "$@"
