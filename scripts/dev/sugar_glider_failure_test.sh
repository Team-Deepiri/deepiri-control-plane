#!/usr/bin/env bash
# Sugar Glider failure-path test alias (legacy script: sidecar_failure_test.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/sidecar_failure_test.sh" "$@"
