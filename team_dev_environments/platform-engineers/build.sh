#!/bin/bash
# Platform Engineers - Build script
# Builds ALL services using docker-compose.dev.yml

set -e

cd "$(dirname "$0")/../.." || exit 1

# BuildKit is required for Docker secrets used by private GitHub Packages.
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "❌ GITHUB_TOKEN is required to install @team-deepiri/shared-utils from GitHub Packages."
  echo "   Create a token with read:packages access, then run: export GITHUB_TOKEN=..."
  exit 1
fi

echo "🔨 Building Platform Engineers services (All Services)..."
echo "   (Using docker-compose.dev.yml)"
echo ""

# Build services sequentially. Windows Docker Desktop / WSL2 runs out of
# runc/BuildKit resources when 10+ npm installs run in parallel, causing
# "runc run failed: container process is already dead" and snapshot errors.
# Sequential builds are slower but reliable.
SERVICES=$(docker compose -f docker-compose.dev.yml config --services)
failed=()
for svc in $SERVICES; do
  echo ""
  echo "── Building $svc ──"
  if ! docker compose -f docker-compose.dev.yml build "$svc"; then
    echo "❌ $svc failed"
    failed+=("$svc")
  fi
done

if [ ${#failed[@]} -gt 0 ]; then
  echo ""
  echo "❌ Failed services: ${failed[*]}"
  exit 1
fi

echo ""
echo "✅ Platform Engineers services built successfully!"
