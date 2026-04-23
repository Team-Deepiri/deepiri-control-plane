#!/bin/bash
# Platform Engineers - Build script (No Cache)
# Builds ALL services using docker-compose.dev.yml (no cache)

set -e

cd "$(dirname "$0")/../.." || exit 1

# Enable BuildKit for better builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "❌ GITHUB_TOKEN is required to install @team-deepiri/shared-utils from GitHub Packages."
  echo "   Create a token with read:packages access, then run: export GITHUB_TOKEN=..."
  exit 1
fi

echo "🔨 Building Platform Engineers services (All Services, No Cache)..."
echo "   (Using docker-compose.dev.yml)"
echo ""

# Build all services using docker-compose.dev.yml with --no-cache
docker compose -f docker-compose.dev.yml build --no-cache

echo "✅ Platform Engineers services built successfully!"
