#!/usr/bin/env bash
# Sugar Glider gRPC smoke test alias (legacy script: sidecar_grpc_smoke_test.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/sidecar_grpc_smoke_test.sh" "$@"
