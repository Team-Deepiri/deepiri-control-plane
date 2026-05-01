#!/bin/bash
# AI Team - Pull Submodules Script
# This script initializes and updates all submodules required by the AI Team

set -e

echo "🤖 AI Team - Pulling Submodules"
echo "================================"
echo ""

# Navigate to main repository root
# Script is at: team_submodule_commands/ai-team/pull_submodules.sh
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

# AI Team required submodules
echo "🔧 Initializing AI Team submodules..."
echo ""

# Ensure platform-services/backend directory exists
mkdir -p platform-services/backend

# diri-cyrex - AI/ML service
echo "  📦 diri-cyrex (AI/ML Service)..."
git submodule update --init --recursive diri-cyrex
echo "    ✅ diri-cyrex initialized"
echo ""

# diri-persola - Personalized Agentic Framework
echo "  📦 diri-persola (Persola - Personalized Agentic Framework)..."
git submodule update --init --recursive diri-persola
echo "    ✅ diri-persola initialized"
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

# deepiri-api-gateway - API Gateway (read-only access)
echo "  📦 deepiri-api-gateway (API Gateway)..."
git submodule update --init --recursive platform-services/backend/deepiri-api-gateway
if [ ! -f "platform-services/backend/deepiri-api-gateway/.git" ] && [ ! -d "platform-services/backend/deepiri-api-gateway/.git" ]; then
    echo "    ❌ ERROR: deepiri-api-gateway not cloned correctly!"
    exit 1
fi
echo "    ✅ api-gateway initialized at: $(pwd)/platform-services/backend/deepiri-api-gateway"
echo ""

# deepiri-prismpipe - PrismPipe (Capability-Routed API Pipeline)
echo "  📦 deepiri-prismpipe (PrismPipe - Capability-Routed API Pipeline)..."
mkdir -p platform-services/shared/deepiri-prismpipe
git submodule update --init --recursive platform-services/shared/deepiri-prismpipe 2>&1 || true
if [ ! -d "platform-services/shared/deepiri-prismpipe/.git" ] && [ ! -f "platform-services/shared/deepiri-prismpipe/.git" ]; then
    echo "    ⚠️  WARNING: deepiri-prismpipe not cloned correctly!"
else
    echo "    ✅ prismpipe initialized at: $(pwd)/platform-services/shared/deepiri-prismpipe"
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
git submodule update --init diri-cyrex
ensure_submodule_on_main "diri-cyrex"
echo "    ✅ diri-cyrex initialized at platform-pinned commit"
git submodule update --init platform-services/shared/deepiri-shared-utils 2>/dev/null || true
ensure_submodule_on_main "platform-services/shared/deepiri-shared-utils"
echo "    ✅ shared-utils initialized at platform-pinned commit"
git submodule update --init diri-persola
ensure_submodule_on_main "diri-persola"
echo "    ✅ diri-persola initialized at platform-pinned commit"
git submodule update --init platform-services/backend/deepiri-api-gateway
ensure_submodule_on_main "platform-services/backend/deepiri-api-gateway"
echo "    ✅ api-gateway initialized at platform-pinned commit"
git submodule update --init deepiri-modelkit 2>/dev/null || true
ensure_submodule_on_main "deepiri-modelkit"
echo "    ✅ modelkit initialized at platform-pinned commit"
git submodule update --init platform-services/shared/deepiri-prismpipe 2>/dev/null || true
ensure_submodule_on_main "platform-services/shared/deepiri-prismpipe"
echo "    ✅ prismpipe initialized at platform-pinned commit"
echo ""

# Show status
echo "📊 Submodule Status:"
echo ""
git submodule status diri-cyrex
git submodule status diri-persola
git submodule status platform-services/backend/deepiri-api-gateway
git submodule status deepiri-modelkit 2>/dev/null || echo "  ⚠️  deepiri-modelkit (not initialized)"
git submodule status platform-services/shared/deepiri-prismpipe 2>/dev/null || echo "  ⚠️  deepiri-prismpipe (not initialized)"
git submodule status platform-services/shared/deepiri-shared-utils 2>/dev/null || echo "  ⚠️  deepiri-shared-utils (not initialized)"
echo ""

echo "✅ AI Team submodules ready!"
echo ""
echo "📋 Quick Commands:"
echo "  - Check status: git submodule status diri-cyrex"
echo "  - Check status: git submodule status diri-persola"
echo "  - Check status: git submodule status platform-services/backend/deepiri-api-gateway"
echo "  - Check status: git submodule status deepiri-modelkit"
echo "  - Check status: git submodule status platform-services/shared/deepiri-prismpipe"
echo "  - Update: git submodule update --init diri-cyrex"
echo "  - Update: git submodule update --init diri-persola"
echo "  - Update: git submodule update --init platform-services/backend/deepiri-api-gateway"
echo "  - Update: git submodule update --init deepiri-modelkit"
echo "  - Update: git submodule update --init platform-services/shared/deepiri-prismpipe"
echo "  - Work in cyrex: cd diri-cyrex"
echo "  - Work in api gateway: cd platform-services/backend/deepiri-api-gateway"
echo "  - Work in modelkit: cd deepiri-modelkit"
echo "  - Work in prismpipe: cd platform-services/shared/deepiri-prismpipe"
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

