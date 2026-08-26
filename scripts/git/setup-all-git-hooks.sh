#!/bin/sh
# Master script to set up Git hooks for all Deepiri repositories

echo "🔧 Setting up Git hooks for all Deepiri repositories..."
echo ""

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT" || exit 1

# Function to setup hooks in a directory
setup_hooks() {
    local repo_path=$1
    local repo_name=$2
    
    if [ -d "$repo_path" ] && [ -f "$repo_path/.git-hooks/pre-push" ]; then
        echo "📦 Setting up hooks for $repo_name..."
        cd "$repo_path" || return
        if [ -f "setup-hooks.sh" ]; then
            chmod +x setup-hooks.sh
            ./setup-hooks.sh
        else
            git config core.hooksPath .git-hooks
            chmod +x .git-hooks/pre-push
            echo "✔ Hooks configured for $repo_name"
        fi
        cd "$REPO_ROOT" || return
    else
        echo "⚠️  Skipping $repo_name (not found or hooks not present)"
    fi
}

# Setup hooks for main repo (deepiri-control-plane)
echo "🏠 Setting up hooks for main repository (deepiri-control-plane)..."
if [ -f ".git-hooks/pre-push" ]; then
    git config core.hooksPath .git-hooks
    chmod +x .git-hooks/pre-push
    echo "✔ Main repository hooks configured"
else
    echo "⚠️  Warning: Main repository hooks not found"
fi
echo ""

# Setup hooks for all submodules
echo "📚 Setting up hooks for submodules..."
setup_hooks "deepiri-core-api" "deepiri-core-api"
setup_hooks "deepiri-web-frontend" "deepiri-web-frontend"
setup_hooks "platform-services/backend/deepiri-api-gateway" "deepiri-api-gateway"
setup_hooks "platform-services/backend/deepiri-auth-service" "deepiri-auth-service"
setup_hooks "platform-services/backend/deepiri-external-bridge-service" "deepiri-external-bridge-service"
setup_hooks "diri-cyrex" "diri-cyrex"

echo ""
echo "✅ Git hooks setup complete for all repositories!"
echo ""
echo "📝 Note: If you're working in a submodule, you may need to:"
echo "   1. cd into the submodule directory"
echo "   2. Run: ./setup-hooks.sh"
echo "   3. Or manually: git config core.hooksPath .git-hooks"

