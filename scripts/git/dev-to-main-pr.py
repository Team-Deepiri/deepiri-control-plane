#!/usr/bin/env python3
"""
Dev-to-Main PR Creator for Deepiri
Creates pull requests across all 24 Deepiri repositories via GitHub CLI.
No local clones required — operates entirely through the GitHub API.

Usage:
  python dev-to-main-pr.py              # interactive mode
  python dev-to-main-pr.py --bulk       # bulk mode (same branch/title for all repos)
  python dev-to-main-pr.py --draft      # create PRs as drafts
  python dev-to-main-pr.py --dry-run    # preview only, no PRs created
"""
import json
import os
import subprocess
import sys
from typing import Optional


class Colors:
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    BOLD = "\033[1m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    GRAY = "\033[0;90m"
    NC = "\033[0m"


GITHUB_ORG = "Team-Deepiri"

DEEPIRI_REPOS = [
    "deepiri-modelkit",
    "deepiri-language-intelligence-service",
    "deepiri-external-bridge-service",
    "deepiri-auth-service",
    "deepiri-api-gateway",
    "diri-helox",
    "deepiri-web-frontend",
    "deepiri-core-api",
    "deepiri-gpu-utils",
    "deepiri-dataset-processor",
    "diri-agent-testing-utils",
    "diri-cyrex",
    "deepiri-uqe",
    "deepiri-emotion-desktop",
    "deepiri-zepgpu",
    "deepiri-mudspeed",
    "deepiri-prismpipe",
    "deepiri-landing",
    "deepiri-demo",
    "deepiri-platform",
    "diri-persola",
    "deepiri-sorge",
    "diri-agent-toolbox",
    "deepiri-pkg-version-manager",
]


# ---------------------------------------------------------------------------
# GitHub helpers (all via gh CLI, no local git needed)
# ---------------------------------------------------------------------------

def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh"] + list(args), capture_output=True, text=True)


def gh_api(path: str, method: str = "GET", fields: Optional[dict] = None) -> tuple[int, any]:
    cmd = ["gh", "api", path, "-X", method]
    if fields:
        for k, v in fields.items():
            cmd += ["-f", f"{k}={v}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        data = {}
    return result.returncode, data


def check_gh_auth() -> bool:
    return gh("auth", "status").returncode == 0


def repo_slug(repo_name: str) -> str:
    return f"{GITHUB_ORG}/{repo_name}"


def get_repo_branches(repo_name: str) -> list[str]:
    code, data = gh_api(f"repos/{repo_slug(repo_name)}/branches?per_page=100")
    if code != 0 or not isinstance(data, list):
        return []
    return [b["name"] for b in data]


def get_default_branch(repo_name: str) -> str:
    code, data = gh_api(f"repos/{repo_slug(repo_name)}")
    if code == 0 and isinstance(data, dict):
        return data.get("default_branch", "main")
    return "main"


def get_compare(repo_name: str, base: str, head: str) -> dict:
    """Returns GitHub compare data: ahead_by, commits list, files."""
    code, data = gh_api(f"repos/{repo_slug(repo_name)}/compare/{base}...{head}")
    if code != 0 or not isinstance(data, dict):
        return {}
    return data


def pr_exists(repo_name: str, head_branch: str, base_branch: str) -> Optional[str]:
    result = gh(
        "pr", "list",
        "--repo", repo_slug(repo_name),
        "--head", head_branch,
        "--base", base_branch,
        "--json", "url",
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            prs = json.loads(result.stdout)
            if prs:
                return prs[0].get("url", "")
        except Exception:
            pass
    return None


def create_pr(
    repo_name: str,
    head_branch: str,
    base_branch: str,
    title: str,
    body: str,
    draft: bool = False,
) -> tuple[bool, str]:
    args = [
        "pr", "create",
        "--repo", repo_slug(repo_name),
        "--head", head_branch,
        "--base", base_branch,
        "--title", title,
        "--body", body,
    ]
    if draft:
        args.append("--draft")
    result = gh(*args)
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, (result.stderr or result.stdout).strip()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_banner():
    print(f"{Colors.CYAN}")
    print(f"╔{'═'*60}╗")
    print(f"║{'  Dev → Main PR Creator (Deepiri)  ':^60}║")
    print(f"║{'  24 repos · GitHub API · no local clones needed  ':^60}║")
    print(f"╚{'═'*60}╝{Colors.NC}")
    print()


def print_repo_header(name: str, index: int, total: int):
    label = f"[{index}/{total}] {GITHUB_ORG}/{name}"
    print(f"\n{Colors.CYAN}╔{'─'*58}╗{Colors.NC}")
    print(f"{Colors.CYAN}║ {Colors.BOLD}{label:<57}{Colors.CYAN}║{Colors.NC}")
    print(f"{Colors.CYAN}╚{'─'*58}╝{Colors.NC}")


def select_branch(prompt: str, branches: list[str], allow_custom: bool = True) -> Optional[str]:
    if not branches:
        if allow_custom:
            print(f"  {Colors.CYAN}No branches found. Enter name (blank to skip): {Colors.NC}", end="")
            val = input().strip()
            return val if val else None
        return None

    for i, b in enumerate(branches):
        print(f"    {Colors.BLUE}{i + 1}){Colors.NC} {b}")

    suffix = ", or type a name" if allow_custom else ""
    print(f"  {Colors.CYAN}{prompt} [1-{len(branches)}{suffix}, 's' to skip]: {Colors.NC}", end="")
    val = input().strip()

    if val.lower() == "s":
        return None
    try:
        idx = int(val) - 1
        if 0 <= idx < len(branches):
            return branches[idx]
        print(f"  {Colors.RED}Invalid number, skipping.{Colors.NC}")
        return None
    except ValueError:
        return val if (allow_custom and val) else None


# ---------------------------------------------------------------------------
# Per-repo handler
# ---------------------------------------------------------------------------

def handle_repo(
    repo_name: str,
    index: int,
    total: int,
    bulk_head: Optional[str],
    bulk_base: Optional[str],
    bulk_title: Optional[str],
    bulk_body: Optional[str],
    draft: bool,
    dry_run: bool,
) -> dict:
    print_repo_header(repo_name, index, total)

    print(f"  {Colors.GRAY}Loading branches from GitHub...{Colors.NC}", end="", flush=True)
    branches = get_repo_branches(repo_name)
    if branches is None:
        branches = []
    print(f" {len(branches)} found")

    if not branches:
        print(f"  {Colors.YELLOW}Could not load branches (repo may be empty or inaccessible), skipping.{Colors.NC}")
        return {"repo": repo_name, "status": "skipped", "reason": "no branches accessible"}

    # Head branch
    if bulk_head:
        if bulk_head not in branches:
            print(f"  {Colors.YELLOW}Branch '{bulk_head}' not found in {repo_name}, skipping.{Colors.NC}")
            return {"repo": repo_name, "status": "skipped", "reason": f"branch '{bulk_head}' not found"}
        head_branch = bulk_head
    else:
        print(f"  {Colors.CYAN}Select HEAD (feature/dev) branch:{Colors.NC}")
        head_branch = select_branch("Head branch", branches)
        if not head_branch:
            return {"repo": repo_name, "status": "skipped", "reason": "user skipped"}

    # Base branch
    if bulk_base:
        base_branch = bulk_base
    else:
        default = get_default_branch(repo_name)
        base_candidates = list(dict.fromkeys(
            [b for b in [default, "main", "master", "develop"] if b in branches]
        ))
        print(f"  {Colors.CYAN}Select BASE branch (default: {default}):{Colors.NC}")
        base_branch = select_branch("Base branch", base_candidates) or default

    print(f"  {Colors.GREEN}{head_branch}{Colors.NC} → {Colors.BLUE}{base_branch}{Colors.NC}")

    if head_branch == base_branch:
        print(f"  {Colors.YELLOW}Head and base are the same branch, skipping.{Colors.NC}")
        return {"repo": repo_name, "status": "skipped", "reason": "same branch"}

    # Check existing PR
    existing = pr_exists(repo_name, head_branch, base_branch)
    if existing:
        print(f"  {Colors.YELLOW}PR already exists: {existing}{Colors.NC}")
        return {"repo": repo_name, "status": "exists", "url": existing}

    # Compare branches via GitHub API
    print(f"  {Colors.GRAY}Comparing branches...{Colors.NC}", end="", flush=True)
    compare = get_compare(repo_name, base_branch, head_branch)
    ahead_by = compare.get("ahead_by", 0)
    commits = compare.get("commits", [])
    files = compare.get("files", [])
    print(f" {ahead_by} commit(s) ahead")

    if ahead_by == 0:
        print(f"  {Colors.YELLOW}No commits ahead of '{base_branch}', skipping.{Colors.NC}")
        return {"repo": repo_name, "status": "skipped", "reason": "no commits ahead"}

    if commits:
        print(f"  {Colors.CYAN}Recent commits:{Colors.NC}")
        for c in commits[:5]:
            msg = c.get("commit", {}).get("message", "").split("\n")[0]
            sha = c.get("sha", "")[:7]
            print(f"    {Colors.GRAY}{sha} {msg}{Colors.NC}")
        if len(commits) > 5:
            print(f"    {Colors.GRAY}... and {len(commits) - 5} more{Colors.NC}")

    if files:
        additions = sum(f.get("additions", 0) for f in files)
        deletions = sum(f.get("deletions", 0) for f in files)
        print(f"  {Colors.CYAN}Changed files: {len(files)}  +{additions} -{deletions}{Colors.NC}")

    # PR title
    if bulk_title:
        title = bulk_title
    else:
        first_msg = ""
        if commits:
            first_msg = commits[-1].get("commit", {}).get("message", "").split("\n")[0]
        default_title = first_msg or f"Merge {head_branch} into {base_branch}"
        print(f"  {Colors.CYAN}PR title [{default_title}]: {Colors.NC}", end="")
        t = input().strip()
        title = t if t else default_title

    # PR body
    if bulk_body:
        body = bulk_body
    else:
        auto_body = "## Summary\n\n"
        for c in commits[:10]:
            msg = c.get("commit", {}).get("message", "").split("\n")[0]
            auto_body += f"- {msg}\n"
        auto_body += "\n🤖 Created with dev-to-main-pr.py"
        print(f"  {Colors.CYAN}Use auto-generated body? [Y/n]: {Colors.NC}", end="")
        if input().strip().lower() not in ("", "y"):
            print(f"  {Colors.CYAN}Enter body (use \\n for newlines): {Colors.NC}", end="")
            b = input().strip()
            body = b.replace("\\n", "\n") if b else auto_body
        else:
            body = auto_body

    if dry_run:
        print(f"  {Colors.YELLOW}[DRY RUN] Would create: '{title}' ({head_branch} → {base_branch}){Colors.NC}")
        return {"repo": repo_name, "status": "dry_run", "title": title}

    print(f"  {Colors.GRAY}Creating PR...{Colors.NC}")
    ok, url_or_err = create_pr(repo_name, head_branch, base_branch, title, body, draft=draft)
    if ok:
        print(f"  {Colors.GREEN}PR created: {url_or_err}{Colors.NC}")
        return {"repo": repo_name, "status": "created", "url": url_or_err}
    else:
        print(f"  {Colors.RED}Failed: {url_or_err}{Colors.NC}")
        return {"repo": repo_name, "status": "failed", "error": url_or_err}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    draft = "--draft" in sys.argv or "-d" in sys.argv
    bulk_mode = "--bulk" in sys.argv or "-b" in sys.argv

    print_banner()

    if not check_gh_auth():
        print(f"{Colors.RED}Error: GitHub CLI not authenticated. Run 'gh auth login' first.{Colors.NC}")
        sys.exit(1)

    if dry_run:
        print(f"{Colors.YELLOW}[DRY RUN MODE — no PRs will be created]{Colors.NC}\n")
    if draft:
        print(f"{Colors.YELLOW}[DRAFT mode — PRs will be created as drafts]{Colors.NC}\n")

    print(f"{Colors.CYAN}Targeting org: {Colors.BOLD}{GITHUB_ORG}{Colors.NC}")
    print(f"{Colors.CYAN}Repos: {len(DEEPIRI_REPOS)} hardcoded{Colors.NC}\n")

    # Bulk mode config
    bulk_head: Optional[str] = None
    bulk_base: Optional[str] = None
    bulk_title: Optional[str] = None
    bulk_body: Optional[str] = None

    if bulk_mode:
        print(f"{Colors.CYAN}╔{'─'*58}╗{Colors.NC}")
        print(f"{Colors.CYAN}║ {'BULK MODE — same settings applied to all repos':^57}║{Colors.NC}")
        print(f"{Colors.CYAN}╚{'─'*58}╝{Colors.NC}")
        print(f"{Colors.CYAN}Head (feature/dev) branch name: {Colors.NC}", end="")
        bulk_head = input().strip() or None
        print(f"{Colors.CYAN}Base branch (blank = each repo's default): {Colors.NC}", end="")
        bulk_base = input().strip() or None
        print(f"{Colors.CYAN}PR title (blank = auto per repo): {Colors.NC}", end="")
        bulk_title = input().strip() or None
        print(f"{Colors.CYAN}PR body (blank = auto per repo, use \\n for newlines): {Colors.NC}", end="")
        b = input().strip()
        bulk_body = b.replace("\\n", "\n") if b else None
        print()

    # Scope selection
    print(f"{Colors.CYAN}Process all {len(DEEPIRI_REPOS)} repos? [Y/n/select]: {Colors.NC}", end="")
    scope = input().strip().lower()

    if scope == "n":
        print(f"{Colors.YELLOW}Aborted.{Colors.NC}")
        sys.exit(0)

    selected = list(DEEPIRI_REPOS)
    if scope == "select":
        print(f"\n{Colors.CYAN}Select repos (comma-separated numbers):{Colors.NC}")
        for i, r in enumerate(DEEPIRI_REPOS):
            print(f"  {Colors.BLUE}{i + 1}){Colors.NC} {r}")
        print(f"{Colors.CYAN}Selection: {Colors.NC}", end="")
        sel = input().strip()
        try:
            indices = [int(x.strip()) - 1 for x in sel.split(",")]
            selected = [DEEPIRI_REPOS[i] for i in indices if 0 <= i < len(DEEPIRI_REPOS)]
        except ValueError:
            print(f"{Colors.RED}Invalid selection, processing all.{Colors.NC}")

    print()

    # Process each repo
    results = []
    for i, repo_name in enumerate(selected, 1):
        result = handle_repo(
            repo_name=repo_name,
            index=i,
            total=len(selected),
            bulk_head=bulk_head,
            bulk_base=bulk_base,
            bulk_title=bulk_title,
            bulk_body=bulk_body,
            draft=draft,
            dry_run=dry_run,
        )
        results.append(result)

        if i < len(selected):
            print(f"\n{Colors.GRAY}[Enter] Next repo  [q] Stop: {Colors.NC}", end="")
            if input().strip().lower() == "q":
                print(f"{Colors.YELLOW}Stopped early.{Colors.NC}")
                break

    # Summary
    groups = {
        "created": (Colors.GREEN, "Created"),
        "exists":  (Colors.YELLOW, "Already exists"),
        "dry_run": (Colors.YELLOW, "Dry-run"),
        "skipped": (Colors.YELLOW, "Skipped"),
        "failed":  (Colors.RED,    "Failed"),
    }

    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.BOLD}Summary{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    for key, (color, label) in groups.items():
        items = [r for r in results if r["status"] == key]
        if not items:
            continue
        print(f"  {color}{label} ({len(items)}):{Colors.NC}")
        for r in items:
            detail = r.get("url") or r.get("title") or r.get("reason") or r.get("error") or ""
            print(f"    {Colors.GRAY}{r['repo']}{': ' + detail if detail else ''}{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")


if __name__ == "__main__":
    main()
