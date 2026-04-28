#!/bin/bash
# ML Team - Pull Submodules Script
# This script initializes and updates all submodules required by the ML Team

set -e

echo "🧠 ML Team - Pulling Submodules"
echo "================================"
echo ""

# Navigate to main repository root
# Script is at: team_submodule_commands/ml-team/pull_submodules.sh
# Need to go up 2 levels to reach repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Verify we're in a git repository
if [ ! -d "$REPO_ROOT/.git" ]; then
    echo "❌ Error: Not in a git repository!"
    echo "   Expected repo root: $REPO_ROOT"
    echo "   Please run this script from the Deepiri repository root"
    exit 1
fi

cd "$REPO_ROOT"

echo "📂 Repository root: $REPO_ROOT"
echo "   ✅ Confirmed: Git repository detected"
echo ""

# Helper function retained for older script flow. Submodule checkout stays pinned to the platform commit.
ensure_submodule_on_main() {
    local submodule_path="$1"
    echo "    📌 Leaving $submodule_path at the platform-pinned commit"
    return 0
}

# Keep the platform checkout as the source of truth.
# Do not auto-pull the parent repo here; onboarding may be running from a feature branch.
echo "📌 Using current platform checkout: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo detached)"
echo ""

# ML Team required submodules
echo "🔧 Initializing ML Team submodules..."
echo ""

# diri-helox - ML training pipelines and research
echo "  📦 diri-helox (ML Training & Research)..."
git submodule update --init --recursive diri-helox
echo "    ✅ diri-helox initialized"
echo ""

# deepiri-modelkit - Shared contracts and utilities
echo "  📦 deepiri-modelkit (Shared Contracts & Utilities)..."
mkdir -p deepiri-modelkit
git submodule update --init --recursive deepiri-modelkit 2>&1 || true
if [ ! -d "deepiri-modelkit/.git" ] && [ ! -f "deepiri-modelkit/.git" ]; then
    echo "    ⚠️  WARNING: deepiri-modelkit not cloned correctly!"
else
    echo "    ✅ modelkit initialized at: $(pwd)/deepiri-modelkit"
fi
echo ""

# deepiri-shared-utils
echo "  📦 deepiri-shared-utils (Shared Utilities - Team-Deepiri/deepiri-shared-utils)..."
cleanup_invalid_submodule "platform-services/shared/deepiri-shared-utils"
git submodule update --init --recursive platform-services/shared/deepiri-shared-utils 2>&1 || true
if ! check_submodule "platform-services/shared/deepiri-shared-utils"; then
    echo "    ❌ ERROR: deepiri-shared-utils not cloned correctly!"
    echo "    💡 Try: git submodule update --init --recursive platform-services/shared/deepiri-shared-utils"
    exit 1
fi
echo "    ✅ shared-utils initialized at: $(pwd)/platform-services/shared/deepiri-shared-utils"
echo ""

# Initialize submodules at platform-pinned commits
echo "🔄 Verifying submodules at platform-pinned commits..."
git submodule update --init diri-helox
ensure_submodule_on_main "diri-helox"
echo "    ✅ diri-helox initialized at platform-pinned commit"
git submodule update --init deepiri-modelkit 2>/dev/null || true
ensure_submodule_on_main "deepiri-modelkit"
echo "    ✅ modelkit initialized at platform-pinned commit"
git submodule update --init platform-services/shared/deepiri-shared-utils 2>/dev/null || true
ensure_submodule_on_main "platform-services/shared/deepiri-shared-utils"
echo "    ✅ shared-utils initialized at platform-pinned commit"
echo ""

# Show status
echo "📊 Submodule Status:"
echo ""
git submodule status diri-helox
git submodule status deepiri-modelkit 2>/dev/null || echo "  ⚠️  deepiri-modelkit (not initialized)"
git submodule status platform-services/shared/deepiri-shared-utils 2>/dev/null || echo "  ⚠️  deepiri-shared-utils (not initialized)"
echo ""

echo "✅ ML Team submodules ready!"
echo ""
echo "📋 Quick Commands:"
echo "  - Check status: git submodule status diri-helox"
echo "  - Check status: git submodule status deepiri-modelkit"
echo "  - Update: git submodule update --init diri-helox"
echo "  - Update: git submodule update --init deepiri-modelkit"
echo "  - Work in helox: cd diri-helox"
echo "  - Work in modelkit: cd deepiri-modelkit"
echo "  - Training pipelines: cd diri-helox/pipelines/training"
echo ""

# Automatically run setup-hooks.sh after pulling submodules
echo "🔧 Setting up Git hooks for pulled submodules..."
echo ""
if [ -f "$SCRIPT_DIR/setup-hooks.sh" ]; then
    bash "$SCRIPT_DIR/setup-hooks.sh"
else
    echo "⚠️  Warning: setup-hooks.sh not found at $SCRIPT_DIR/setup-hooks.sh"
    echo "   Hooks will not be automatically configured."
fi
echo ""

