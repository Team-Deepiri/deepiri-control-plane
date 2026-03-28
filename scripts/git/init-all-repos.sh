#!/bin/bash
# init-all-repos.sh
# Bootstraps the full Team-Deepiri workspace in one shot:
#
#   1. Repos that are submodules of deepiri-platform
#        → git submodule update --init <path>
#   2. Repos that are submodules of any platform submodule (nested)
#        → cd <parent> && git submodule update --init <nested-path>
#   3. All other org repos (external)
#        → git clone <ssh-url> into the sibling directory of deepiri-platform
#
# Run this from anywhere inside the deepiri-platform repo tree.

# Don't use set -e — we want to continue processing even if individual repos fail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT" || { echo "Error: Could not change to repository root."; exit 1; }

PLATFORM_NAME="$(basename "$REPO_ROOT")"
SIBLING_DIR="$(dirname "$REPO_ROOT")"
ORG="Team-Deepiri"

echo "Init All Repos"
echo "=============="
echo ""
echo "  Platform : $REPO_ROOT"
echo "  Siblings : $SIBLING_DIR"
echo "  Org      : $ORG"
echo ""

# --- Prerequisites ---

if ! command -v gh &>/dev/null; then
    echo "Error: GitHub CLI (gh) is required. Install from https://cli.github.com"
    exit 1
fi

if ! gh auth status &>/dev/null 2>&1; then
    echo "Error: Not authenticated with GitHub CLI. Run 'gh auth login' first."
    exit 1
fi

if [ ! -f "$REPO_ROOT/.gitmodules" ]; then
    echo "Error: No .gitmodules found. Run this script from within $PLATFORM_NAME."
    exit 1
fi

# --- Step 1: Fetch all org repos ---

echo "Fetching repos from $ORG..."
declare -A ORG_REPO_SSH  # repo_name -> ssh_url

while IFS=$'\t' read -r name ssh_url; do
    [ -n "$name" ] && ORG_REPO_SSH["$name"]="$ssh_url"
done < <(gh repo list "$ORG" --limit 1000 --json name,sshUrl -q '.[] | [.name, .sshUrl] | @tsv' 2>/dev/null)

if [ ${#ORG_REPO_SSH[@]} -eq 0 ]; then
    echo "Error: Could not fetch repos from $ORG. Check your GitHub CLI authentication and org access."
    exit 1
fi

echo "  Found ${#ORG_REPO_SSH[@]} repos in $ORG"
echo ""

# --- Step 2: Parse deepiri-platform's .gitmodules ---
# Builds: PLATFORM_SUB_PATH[repo_name] = submodule path

declare -A PLATFORM_SUB_PATH   # repo_name -> path relative to REPO_ROOT
declare -A PLATFORM_SUB_BY_PATH  # path -> repo_name (reverse lookup)

_parse_gitmodules() {
    local gitmodules_file="$1"
    local -n _out_by_name="$2"
    local -n _out_by_path="$3"

    while IFS= read -r submodule_name; do
        local path url repo_name
        path=$(git config --file "$gitmodules_file" "submodule.$submodule_name.path" 2>/dev/null)
        url=$(git config --file "$gitmodules_file" "submodule.$submodule_name.url" 2>/dev/null)
        repo_name=$(basename "$url" .git)
        [ -n "$path" ] && [ -n "$repo_name" ] || continue
        _out_by_name["$repo_name"]="$path"
        _out_by_path["$path"]="$repo_name"
    done < <(git config --file "$gitmodules_file" --get-regexp 'submodule\..+\.path' \
              | sed -E 's/submodule\.(.+)\.path .+/\1/')
}

_parse_gitmodules "$REPO_ROOT/.gitmodules" PLATFORM_SUB_PATH PLATFORM_SUB_BY_PATH

echo "Platform submodules: ${#PLATFORM_SUB_PATH[@]}"
for repo in "${!PLATFORM_SUB_PATH[@]}"; do
    echo "   ${PLATFORM_SUB_PATH[$repo]}"
done | sort
echo ""

# --- Step 3: Parse nested .gitmodules in each platform submodule ---
# Builds: NESTED_SUB_PARENT[repo_name] = parent path
#         NESTED_SUB_RELPATH[repo_name] = path relative to parent

declare -A NESTED_SUB_PARENT   # repo_name -> parent submodule path (relative to REPO_ROOT)
declare -A NESTED_SUB_RELPATH  # repo_name -> nested path (relative to parent)

for parent_path in "${!PLATFORM_SUB_BY_PATH[@]}"; do
    nested_gitmodules="$REPO_ROOT/$parent_path/.gitmodules"
    [ -f "$nested_gitmodules" ] || continue

    declare -A _nested_by_name _nested_by_path
    _parse_gitmodules "$nested_gitmodules" _nested_by_name _nested_by_path

    for nested_repo in "${!_nested_by_name[@]}"; do
        NESTED_SUB_PARENT["$nested_repo"]="$parent_path"
        NESTED_SUB_RELPATH["$nested_repo"]="${_nested_by_name[$nested_repo]}"
    done
    unset _nested_by_name _nested_by_path
done

if [ ${#NESTED_SUB_PARENT[@]} -gt 0 ]; then
    echo "Nested submodules found: ${#NESTED_SUB_PARENT[@]}"
    for repo in "${!NESTED_SUB_PARENT[@]}"; do
        echo "   ${NESTED_SUB_PARENT[$repo]}/${NESTED_SUB_RELPATH[$repo]}"
    done | sort
    echo ""
fi

# --- Step 4: Categorize and process ---

echo "Processing all ${#ORG_REPO_SSH[@]} repos..."
echo ""

SUCCESS_COUNT=0
ALREADY_DONE=()
FAILED=()
SKIPPED=()

for repo_name in $(echo "${!ORG_REPO_SSH[@]}" | tr ' ' '\n' | sort); do
    ssh_url="${ORG_REPO_SSH[$repo_name]}"

    # Skip the platform repo itself
    if [ "$repo_name" = "$PLATFORM_NAME" ]; then
        continue
    fi

    # ── Case 1: Direct submodule of deepiri-platform ──────────────────────
    if [ -n "${PLATFORM_SUB_PATH[$repo_name]+_}" ]; then
        submodule_path="${PLATFORM_SUB_PATH[$repo_name]}"
        echo "📦 [submodule] $repo_name"
        echo "   Path: $submodule_path"

        if git submodule update --init "$submodule_path" 2>&1 | sed 's/^/   /'; then
            echo "   ✅ Initialized"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo "   ❌ Failed to initialize submodule"
            FAILED+=("$repo_name (submodule init failed)")
        fi
        echo ""
        continue
    fi

    # ── Case 2: Nested submodule of a platform submodule ──────────────────
    if [ -n "${NESTED_SUB_PARENT[$repo_name]+_}" ]; then
        parent_path="${NESTED_SUB_PARENT[$repo_name]}"
        nested_path="${NESTED_SUB_RELPATH[$repo_name]}"
        echo "📦 [nested submodule] $repo_name"
        echo "   Path: $parent_path/$nested_path"

        parent_abs="$REPO_ROOT/$parent_path"
        if [ ! -d "$parent_abs" ] || [ ! -f "$parent_abs/.git" ] && [ ! -d "$parent_abs/.git" ]; then
            echo "   ⚠️  Parent submodule not initialized yet — initialize the parent first"
            SKIPPED+=("$repo_name (parent '$parent_path' not initialized)")
            echo ""
            continue
        fi

        cd "$parent_abs" || { FAILED+=("$repo_name (cd to parent failed)"); cd "$REPO_ROOT"; echo ""; continue; }
        if git submodule update --init "$nested_path" 2>&1 | sed 's/^/   /'; then
            echo "   ✅ Initialized"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo "   ❌ Failed to initialize nested submodule"
            FAILED+=("$repo_name (nested submodule init failed)")
        fi
        cd "$REPO_ROOT" || exit 1
        echo ""
        continue
    fi

    # ── Case 3: External repo — clone/update as sibling ───────────────────
    target_dir="$SIBLING_DIR/$repo_name"
    echo "🌐 [external] $repo_name"
    echo "   Target: $target_dir"

    if [ -d "$target_dir/.git" ] || [ -f "$target_dir/.git" ]; then
        echo "   Already cloned — pulling latest..."
        cd "$target_dir" || { FAILED+=("$repo_name (cd failed)"); cd "$REPO_ROOT"; echo ""; continue; }
        if git pull --ff-only 2>&1 | sed 's/^/   /'; then
            echo "   ✅ Updated"
        else
            echo "   ⚠️  Already up to date or has local changes (no changes made)"
        fi
        ALREADY_DONE+=("$repo_name")
        cd "$REPO_ROOT" || exit 1
    elif [ -d "$target_dir" ]; then
        echo "   ⚠️  Directory exists but is not a git repo — skipping"
        SKIPPED+=("$repo_name (directory exists but not a git repo)")
    else
        if git clone "$ssh_url" "$target_dir" 2>&1 | sed 's/^/   /'; then
            echo "   ✅ Cloned"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo "   ❌ Failed to clone"
            FAILED+=("$repo_name (clone failed)")
        fi
    fi
    echo ""
done

# --- Summary ---

echo "=========================================="
echo "📊 Summary"
echo "=========================================="
echo ""
echo "  ✅ Newly initialized/cloned : $SUCCESS_COUNT"
echo "  🔄 Already present (pulled) : ${#ALREADY_DONE[@]}"
echo "  ⏭️  Skipped                 : ${#SKIPPED[@]}"
echo "  ❌ Failed                   : ${#FAILED[@]}"
echo ""

if [ ${#SKIPPED[@]} -gt 0 ]; then
    echo "⏭️  Skipped repos:"
    for s in "${SKIPPED[@]}"; do echo "   - $s"; done
    echo ""
fi

if [ ${#FAILED[@]} -gt 0 ]; then
    echo "❌ Failed repos:"
    for f in "${FAILED[@]}"; do echo "   - $f"; done
    echo ""
    echo "⚠️  Some repos had issues. See output above for details."
    exit 1
fi

echo "🎉 Done! Workspace is fully initialized."
exit 0
