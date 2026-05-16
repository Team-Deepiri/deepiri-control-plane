#!/bin/bash
# Shared helper — sourced by team build scripts.
# Ensures all deepiri-suite base images are available locally.
# Strategy: check local cache → try GHCR pull → fall back to local build from submodule.

ensure_suite_images() {
  local repo_root="$1"
  local suite_dir="${DEEPIRI_SUITE_CONTEXT:-${repo_root}/deepiri-suite}"

  echo "🐳 Ensuring deepiri-suite base images..."

  local all_ok=true
  for spec in "node:18-alpine:18-alpine" "node:18-slim:18-slim" "node:20-alpine:20-alpine"; do
    local base="${spec%%:*}"
    local tag="${spec##*:}"
    local img="ghcr.io/team-deepiri/deepiri-suite:${tag}"

    if docker image inspect "$img" >/dev/null 2>&1; then
      echo "   ✓ $img (cached)"
      continue
    fi

    echo "   Pulling $img from GHCR..."
    if docker pull "$img" 2>/dev/null; then
      echo "   ✓ $img (pulled)"
      continue
    fi

    echo "   ⚠️  GHCR pull failed — building locally (BASE_IMAGE=$base)"

    if [ ! -f "${suite_dir}/Dockerfile" ]; then
      echo "   ❌ deepiri-suite submodule not initialised at ${suite_dir}"
      echo "      Run: git submodule update --init deepiri-suite"
      all_ok=false
      continue
    fi

    if docker build --build-arg "BASE_IMAGE=${base}" -t "$img" "$suite_dir"; then
      echo "   ✓ $img (built locally)"
    else
      echo "   ❌ Failed to build $img locally"
      all_ok=false
    fi
  done

  echo ""
  if [ "$all_ok" = false ]; then
    return 1
  fi
}
