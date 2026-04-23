#!/bin/bash
# AI Team - Build script
# Builds AI/ML services using docker-compose.dev.yml with service selection

set -e

cd "$(dirname "$0")/../.." || exit 1

# BuildKit is required for Docker secrets used by private GitHub Packages.
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# AI team services
SERVICES=(
  postgres-auth postgres-core postgres-intelligence redis influxdb etcd minio milvus
  cyrex cyrex-interface mlflow
  # jupyter  # DISABLED: No services depend on Jupyter - it's only for manual research/experimentation
  challenge-service api-gateway messaging-service realtime-gateway
  ollama synapse
  # deepiri-prismpipe  # PrismPipe - Capability-Routed API Pipeline (Coming Soon)
)

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "❌ GITHUB_TOKEN is required to install @team-deepiri/shared-utils from GitHub Packages."
  echo "   Create a token with read:packages access, then run: export GITHUB_TOKEN=..."
  exit 1
fi

echo "🔨 Building AI Team services..."
echo "   (Using docker-compose.dev.yml with service selection)"
echo "   Services: ${SERVICES[*]}"
echo ""

# Pull Ollama image (it's a pre-built image, not built from source)
echo "📥 Pulling Ollama Docker image..."
docker pull ollama/ollama:latest || echo "⚠️  Failed to pull Ollama image, will try again during start"
echo ""

# Build services sequentially. Windows Docker Desktop / WSL2 runs out of
# runc/BuildKit resources when 10+ npm installs run in parallel, causing
# "runc run failed: container process is already dead" and snapshot errors.
# Sequential builds are slower but reliable.
failed=()
for svc in "${SERVICES[@]}"; do
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
echo "✅ AI Team services built successfully!"
