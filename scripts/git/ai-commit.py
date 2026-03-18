#!/usr/bin/env python3
"""
AI-Powered Git Commit Script for Deepiri Platform
Analyzes git diffs, groups into logical commits, generates detailed commit messages.
Handles: recursive repo detection, submodule support, segmented commits, interactive selection.
"""
import asyncio
import json
import os
import re
import subprocess
import sys
from typing import Optional

try:
    import httpx
except ImportError:
    print("Error: httpx library required. Install with: pip install httpx")
    sys.exit(1)


class Colors:
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    BOLD = "\033[1m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    NC = "\033[0m"


class Spinner:
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, text: str = ""):
        self.text = text
        self._task: asyncio.Task | None = None
        self._running = False
        self._col_width = 0

    async def _spin(self):
        i = 0
        while self._running:
            frame = self.FRAMES[i % len(self.FRAMES)]
            line = f"  {Colors.CYAN}{frame}{Colors.NC} {self.text}"
            pad = max(0, self._col_width - len(self.text))
            sys.stdout.write(f"\r{line}{' ' * pad}")
            sys.stdout.flush()
            self._col_width = max(self._col_width, len(self.text))
            await asyncio.sleep(0.08)
            i += 1

    async def __aenter__(self):
        self._running = True
        self._task = asyncio.create_task(self._spin())
        return self

    async def __aexit__(self, *_):
        self._running = False
        if self._task:
            await self._task
        sys.stdout.write(f"\r{' ' * (self._col_width + 10)}\r")
        sys.stdout.flush()

    def update(self, text: str):
        self.text = text


def is_git_repo(path: str) -> bool:
    """Check if path is a git repo (dir or file pointing to worktree)"""
    return os.path.isdir(os.path.join(path, ".git")) or os.path.isfile(os.path.join(path, ".git"))


def find_script_git_root() -> str:
    """Find the first git repo containing this script, searching upward"""
    script_path = os.path.dirname(os.path.abspath(__file__))
    current = script_path

    while True:
        if is_git_repo(current):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return os.getcwd()


def parse_gitmodules(root_path: str) -> list[str]:
    """Parse .gitmodules to extract submodule paths"""
    submodule_paths = []
    gitmodules_path = os.path.join(root_path, ".gitmodules")

    if not os.path.isfile(gitmodules_path):
        return submodule_paths

    try:
        with open(gitmodules_path, "r") as f:
            content = f.read()

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("path") and "=" in line:
                path = line.split("=", 1)[1].strip()
                if path and path not in submodule_paths:
                    submodule_paths.append(path)
    except Exception:
        pass

    return submodule_paths


def find_git_repos(root_path: str, search_parents: bool = False, max_depth: int = 3) -> list[dict]:
    """Find all git repos: root, submodules, and sibling repos in parent directories"""
    repos = []
    root_abs = os.path.abspath(root_path)

    root_name = os.path.basename(root_abs) or root_abs
    if is_git_repo(root_abs):
        repos.append({"path": root_abs, "name": root_name, "is_submodule": False})

    submodule_paths = parse_gitmodules(root_abs)
    submodule_abs_paths = set()
    for subpath in submodule_paths:
        full_path = os.path.join(root_abs, subpath)
        if is_git_repo(full_path):
            repos.append({
                "path": full_path,
                "name": os.path.basename(subpath),
                "is_submodule": True,
            })
            submodule_abs_paths.add(os.path.abspath(full_path))

    try:
        result = subprocess.run(
            ["git", "submodule", "status"],
            cwd=root_abs,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        submodule_path = parts[1]
                        full_path = os.path.join(root_abs, submodule_path)
                        full_path_abs = os.path.abspath(full_path)
                        if is_git_repo(full_path) and full_path_abs not in submodule_abs_paths:
                            repos.append({
                                "path": full_path_abs,
                                "name": os.path.basename(submodule_path),
                                "is_submodule": True,
                            })
                            submodule_abs_paths.add(full_path_abs)
    except Exception:
        pass

    return repos


def find_sibling_repos(root_path: str, max_depth: int = 3) -> list[dict]:
    """Search parent directories for sibling git repos"""
    sibling_repos = []
    root_abs = os.path.abspath(root_path)

    current_path = root_abs
    for _ in range(max_depth):
        parent_dir = os.path.dirname(current_path)
        if parent_dir == current_path:
            break

        try:
            if os.path.isdir(parent_dir):
                for entry in os.listdir(parent_dir):
                    entry_path = os.path.join(parent_dir, entry)
                    if os.path.isdir(entry_path) and is_git_repo(entry_path):
                        entry_abs = os.path.abspath(entry_path)
                        if entry_abs != root_abs:
                            sibling_repos.append({
                                "path": entry_abs,
                                "name": entry,
                                "is_submodule": False,
                                "is_sibling": True,
                            })
        except Exception:
            pass

        current_path = parent_dir

    return sibling_repos


def get_git_diff(repo_path: str) -> str:
    """Get all unstaged git changes"""
    try:
        result = subprocess.run(
            ["git", "diff"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return result.stdout
    except Exception:
        return ""


def get_git_status(repo_path: str) -> str:
    """Get git status"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return result.stdout
    except Exception:
        return ""


def get_untracked_files(repo_path: str) -> list[str]:
    """Return untracked files from git status --porcelain"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        untracked = []
        for line in result.stdout.splitlines():
            if line.startswith("?? "):
                path = line[3:].strip()
                full = os.path.join(repo_path, path)
                if os.path.isfile(full):
                    untracked.append(path)
                elif os.path.isdir(full):
                    for root, _, filenames in os.walk(full):
                        for fname in filenames:
                            abs_path = os.path.join(root, fname)
                            rel = os.path.relpath(abs_path, repo_path)
                            untracked.append(rel)
        return untracked
    except Exception:
        return []


def get_new_file_diff(repo_path: str, file_path: str) -> str:
    """Generate a diff-like snippet for an untracked file by reading its content"""
    try:
        full_path = os.path.join(repo_path, file_path)
        with open(full_path, "r", errors="replace") as f:
            content = f.read(8000)
        lines = content.splitlines()
        added = "\n".join(f"+{line}" for line in lines[:200])
        return f"diff --git a/{file_path} b/{file_path}\nnew file\n--- /dev/null\n+++ b/{file_path}\n{added}"
    except Exception:
        return ""


def parse_changed_files(diff_output: str) -> list[dict]:
    """Parse diff output to extract changed files, hunks, and submodule pointers"""
    files = []
    current_file = None
    current_hunks = []
    current_meta: dict = {}
    hunk_num = 0

    for line in diff_output.split("\n"):
        if line.startswith("diff --git"):
            if current_file:
                files.append({"file": current_file, "hunks": current_hunks, **current_meta})
            match = re.search(r"b/(.+)", line)
            current_file = match.group(1) if match else "unknown"
            current_hunks = []
            current_meta = {}
            hunk_num = 0
        elif re.match(r"^index [0-9a-f]+\.\.[0-9a-f]+ 160000", line):
            sha_match = re.match(r"^index ([0-9a-f]+)\.\.([0-9a-f]+)", line)
            if sha_match:
                current_meta["is_submodule_pointer"] = True
                current_meta["old_sha"] = sha_match.group(1)
                current_meta["new_sha"] = sha_match.group(2)
        elif line.startswith("@@"):
            hunk_num += 1
            match = re.match(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@(.*)", line)
            if match:
                current_hunks.append({
                    "hunk_num": hunk_num,
                    "old_start": int(match.group(1)),
                    "old_count": int(match.group(2) or 1),
                    "new_start": int(match.group(3)),
                    "new_count": int(match.group(4) or 1),
                    "header": line,
                })

    if current_file:
        files.append({"file": current_file, "hunks": current_hunks, **current_meta})

    return files


def get_dirty_submodules(repo_path: str, submodule_paths: list[str]) -> list[dict]:
    """Return submodules that have uncommitted changes"""
    dirty = []
    for subpath in submodule_paths:
        full_path = os.path.join(repo_path, subpath)
        if not os.path.isdir(full_path):
            continue
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=full_path,
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                lines = result.stdout.strip().splitlines()
                modified = sum(1 for l in lines if not l.startswith("??"))
                untracked = sum(1 for l in lines if l.startswith("??"))
                dirty.append({
                    "path": subpath,
                    "full_path": full_path,
                    "modified": modified,
                    "untracked": untracked,
                })
        except Exception:
            pass
    return dirty


async def send_to_ollama(base_url: str, model: str, prompt: str, system: str = "") -> str:
    """Send prompt to Ollama and get response"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(f"{base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
    except Exception as e:
        print(f"{Colors.RED}Error sending request to Ollama: {e}{Colors.NC}")
        sys.exit(1)


async def analyze_and_segment_commits(
    base_url: str,
    model: str,
    repo_name: str,
    diff_output: str,
    files: list[dict],
) -> list[dict]:
    """Send diff to Ollama and get structured commit plan"""

    system_prompt = """Group the given file paths into logical git commits. Return ONLY raw JSON, no markdown, no explanation.

Use EXACTLY this schema:
{"commits":[{"description":"verb-first subject max 70 chars","files":["path/a.py","path/b.py"]}]}

Example input:
Dockerfile
app/core/engine.py
app/core/registry.py
app/api/routes.py
docs/README.md

Example output:
{"commits":[{"description":"Update Dockerfile base image","files":["Dockerfile"]},{"description":"Refactor core engine and registry","files":["app/core/engine.py","app/core/registry.py"]},{"description":"Add API routes","files":["app/api/routes.py"]},{"description":"Update README docs","files":["docs/README.md"]}]}

Rules:
- Every file in the input must appear in exactly one commit
- Dockerfile/config = own commit
- docs/ = own commit
- Group only files in the same directory that serve the same purpose
- 6+ input files must produce 3+ commits"""

    files_summary = "\n".join([f["file"] for f in files])

    prompt = f"""Group these {len(files)} changed files from repo "{repo_name}" into logical commits:

{files_summary}

Output only JSON."""

    response = await send_to_ollama(base_url, model, prompt, system=system_prompt)

    debug = os.getenv("AI_COMMIT_DEBUG")
    if debug:
        print(f"\n{Colors.YELLOW}[DEBUG] Raw model response:{Colors.NC}\n{response}\n")

    cleaned = re.sub(r"```(?:json)?\s*", "", response).strip()

    try:
        brace_start = cleaned.find("{")
        if brace_start != -1:
            parsed, _ = json.JSONDecoder().raw_decode(cleaned, brace_start)

            commits = None
            for key in ("commits", "commit_segmentation_plan", "commit_plan", "segments"):
                val = parsed.get(key)
                if isinstance(val, list) and val:
                    commits = val
                    break

            if commits:
                valid_paths = {f["file"] for f in files}
                normalised = []
                for c in commits:
                    raw_files = c.get("files") or c.get("file_paths") or c.get("changed_files") or []
                    actual_files = [f for f in raw_files if f in valid_paths]
                    if actual_files:
                        normalised.append({
                            "description": c.get("description") or c.get("commit_message") or "Update files",
                            "files": actual_files,
                            "reasoning": c.get("reasoning", ""),
                        })
                if normalised:
                    if debug:
                        print(f"{Colors.GREEN}[DEBUG] Parsed {len(normalised)} commit(s){Colors.NC}")
                    return normalised
    except (json.JSONDecodeError, KeyError) as e:
        if debug:
            print(f"{Colors.RED}[DEBUG] JSON parse failed: {e}{Colors.NC}")

    print(f"{Colors.RED}Model returned unparseable response — falling back to single commit.{Colors.NC}")
    print(f"{Colors.YELLOW}Tip: set AI_COMMIT_DEBUG=1 to see raw model output.{Colors.NC}")

    file_list = [f["file"] for f in files]
    return [{"description": f"Update {len(file_list)} files", "files": file_list, "reasoning": "Fallback: model parse failed"}]


async def generate_commit_message(
    base_url: str,
    model: str,
    commit_description: str,
    files: list[str],
    diff_snippet: str = "",
) -> tuple[str, str]:
    """Generate detailed commit message"""

    system_prompt = """You are writing a git commit message. Read the diff carefully and describe EXACTLY what changed.

BAD subject (too vague): "Refactors rate limiter middleware"
GOOD subject (specific): "Add RateLimitMiddleware with Redis token-bucket and X-Forwarded-For IP support"

BAD subject (too vague): "Updates execution engine for rate limiting"
GOOD subject (specific): "Enforce rate limits in ToolRegistry.execute_tool before task dispatch"

Rules:
- Name the actual class, method, function, or config key that changed
- Mention the mechanism if relevant (token bucket, Redis, async, etc.)
- Start with a verb: Adds, Fixes, Refactors, Removes, Implements, Extracts, Enforces, etc.
- Max 100 characters
- No conventional commit prefix

Output ONLY this format:

COMMIT_SUBJECT:
<specific subject naming real things from the diff>

COMMIT_BODY:
- <exact method/class/field name>: what changed and why
- <exact method/class/field name>: what changed and why
- <exact method/class/field name>: what changed and why"""

    diff_context = f"\n\nDiff:\n{diff_snippet[:10000]}" if diff_snippet else ""
    user_prompt = f"""Files: {', '.join(files[:10])}{'...' if len(files) > 10 else ''}{diff_context}"""

    response = await send_to_ollama(base_url, model, user_prompt, system=system_prompt)

    subject = ""
    body = ""

    lines = response.split("\n")
    current_section = None

    for line in lines:
        line = line.strip()
        if line == "COMMIT_SUBJECT:":
            current_section = "subject"
            continue
        elif line == "COMMIT_BODY:":
            current_section = "body"
            continue

        if current_section == "subject":
            subject += line + " "
        elif current_section == "body":
            body += line + " "

    subject = subject.strip()[:100]
    body = body.strip()

    if not subject:
        subject = commit_description[:70]

    return subject, body


DEEPIRI_PR_TEMPLATE = """## IMPORTANT

- PR must be opened from your personal branch → dev
- You must tag @Team-Deepiri/support-team
- You must update Plaky to "Needs QA"
- Never move a feature/bug to "Done" (Done = production release only)

---

## Description

Briefly explain what this PR does and why.

Include:
- Related Issue number
- Plaky feature name
- Component, feature, or system affected
- Purpose of change (feature, bug fix, improvement, refactor, security, etc.)

---

## Changes

List the most important updates in this PR:

- 
- 
- 

Be specific. Include:
- New or updated functions, services, components, or scripts
- Refactoring or structural improvements
- Dependency or configuration changes
- Any significant implementation details

---

## Related

- Issue:
- Plaky:
- Related PRs (optional):

---

## Testing

Explain how you verified your changes and how to test your feature:

Additional testing details:

---

## Important Notes (Optional)

- Known limitations:
- Blockers:
- CI/CD issues unrelated to this PR:
- Dependencies required for testing:

---

## Workflow Checklist (Required)

- [ ] Branch is up to date with dev
- [ ] PR is from your branch → dev (no longer directly into main)
- [ ] PR title follows convention (feat:, fix:, refactor:, etc.)
- [ ] Plaky feature/bug name included above
- [ ] Tagged @Team-Deepiri/support-team
- [ ] Plaky feature moved to "Needs QA"

---

## Review Requests

@Team-Deepiri/support-team
"""


def generate_pr_description(commits: list[dict]) -> str:
    """Generate PR description using Deepiri template with commit summaries"""
    
    commit_log = ""
    for c in commits:
        commit_log += f"- {c.get('subject', 'No description')}\n"
        body = c.get('body', '')
        if body:
            for line in body.splitlines():
                commit_log += f"  {line}\n"
    
    pr_desc = f"""## Description

<!-- Briefly explain what this PR does and why. Include related Issue number, Plaky feature name, component/feature/system affected, and purpose of change. -->

---

## Changes

{commit_log}

---

## Testing

<!-- Explain how you verified your changes and how to test your feature. -->

---

## Important Notes (Optional)

- Known limitations:
- Blockers:
- Dependencies required for testing:

---

## Workflow Checklist (Required)

- [ ] Branch is up to date with dev
- [ ] PR is from your branch → dev (no longer directly into main)
- [ ] PR title follows convention (feat:, fix:, refactor:, etc.)
- [ ] Plaky feature/bug name included above
- [ ] Tagged @Team-Deepiri/support-team
- [ ] Plaky feature moved to "Needs QA"

---

## Review Requests

@Team-Deepiri/support-team
"""
    return pr_desc


def stage_files(repo_path: str, files: list[str]) -> bool:
    """Stage specific files for commit"""
    try:
        subprocess.run(["git", "add"] + files, cwd=repo_path, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}Error staging files: {e}{Colors.NC}")
        return False


def commit_changes(repo_path: str, subject: str, body: str) -> bool:
    """Commit staged changes"""
    full_message = subject
    if body:
        full_message += f"\n\n{body}"

    try:
        subprocess.run(
            ["git", "commit", "-m", full_message],
            cwd=repo_path,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}Error committing: {e}{Colors.NC}")
        return False


def set_upstream_if_needed(repo_path: str) -> bool:
    """Set the current branch to track the remote upstream if not already set"""
    try:
        result = subprocess.run(
            ["git", "status", "-b", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False
        
        branch_line = None
        for line in result.stdout.splitlines():
            if line.startswith("##"):
                branch_line = line
                break
        
        if not branch_line:
            return False
        
        if "..." not in branch_line:
            current_branch = get_current_branch(repo_path)
            if not current_branch:
                return False
            
            upstream_branch = f"origin/{current_branch}"
            try:
                subprocess.run(
                    ["git", "push", "-u", "origin", current_branch],
                    cwd=repo_path,
                    check=True,
                )
                print(f"{Colors.GREEN}✓ Set upstream to {upstream_branch}{Colors.NC}")
                return True
            except subprocess.CalledProcessError as e:
                print(f"{Colors.YELLOW}Warning: Could not set upstream: {e}{Colors.NC}")
                return False
        
        return True
    except Exception as e:
        print(f"{Colors.YELLOW}Warning: Error checking upstream: {e}{Colors.NC}")
        return False


def push_changes(repo_path: str) -> bool:
    """Push changes to remote"""
    try:
        subprocess.run(["git", "push"], cwd=repo_path, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}Error pushing: {e}{Colors.NC}")
        return False


def get_current_branch(repo_path: str) -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path, capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


async def get_ollama_models(base_url: str) -> list:
    """Get list of available models from Ollama"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def confirm_commit(repo_name: str, subject: str, body: str, files: list[str], commit_num: int, total: int) -> bool:
    """Ask user to confirm the commit"""
    print(f"\n{Colors.CYAN}╔{'═'*58}╗{Colors.NC}")
    print(f"{Colors.CYAN}║ Repository: {repo_name:<43}║{Colors.NC}")
    print(f"{Colors.CYAN}║ Commit {commit_num}/{total}:{' '*44}║{Colors.NC}")
    print(f"{Colors.CYAN}╚{'═'*58}╝{Colors.NC}")
    print(f"\n{Colors.CYAN}--- Subject ---{Colors.NC}")
    print(f"{Colors.GREEN}{subject}{Colors.NC}")
    if body:
        print(f"\n{Colors.CYAN}--- Body ---{Colors.NC}")
        print(f"{Colors.YELLOW}{body}{Colors.NC}")
    print(f"\n{Colors.CYAN}--- Files ({len(files)}) ---{Colors.NC}")
    for f in files[:10]:
        print(f"  {Colors.YELLOW}{f}{Colors.NC}")
    if len(files) > 10:
        print(f"  {Colors.YELLOW}... and {len(files) - 10} more{Colors.NC}")
    print()

    response = input(f"{Colors.BLUE}[y] Commit  [s] Skip  [q] Quit  [a] Commit all remaining: {Colors.NC}").strip().lower()
    
    if response == "q":
        print(f"\n{Colors.YELLOW}Quitting...{Colors.NC}")
        sys.exit(0)
    elif response == "s":
        return False
    elif response == "a":
        return "commit_all"
    
    return response == "y"


def extract_diff_for_files(diff_output: str, files: list[str], untracked_diffs: dict | None = None, submodule_pointers: dict | None = None) -> str:
    """Extract diff sections relevant to the given files"""
    sections = []
    current_section = []
    current_file = None
    file_set = set(files)

    for line in diff_output.split("\n"):
        if line.startswith("diff --git"):
            if current_file and current_file in file_set and current_section:
                sections.append("\n".join(current_section))
            match = re.search(r"b/(.+)", line)
            current_file = match.group(1) if match else None
            current_section = [line]
        else:
            current_section.append(line)

    if current_file and current_file in file_set and current_section:
        sections.append("\n".join(current_section))

    if untracked_diffs:
        for f in files:
            if f in untracked_diffs:
                sections.append(untracked_diffs[f])

    if submodule_pointers:
        for f in files:
            if f in submodule_pointers:
                info = submodule_pointers[f]
                sections.append(
                    f"diff --git a/{f} b/{f}\n"
                    f"--- a/{f}\n+++ b/{f}\n"
                    f"-Subproject commit {info['old_sha']}\n"
                    f"+Subproject commit {info['new_sha']}"
                )

    return "\n".join(sections)


def has_changes(repo_path: str) -> bool:
    """Check if a repo has any changes (staged, unstaged, or untracked)"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def get_repos_with_changes(repos: list[dict]) -> tuple[list[dict], list[dict], dict]:
    """
    Separate repos into: dirty_submodules, clean_repos, main_repo
    Also returns a dict of dirty_submodule_paths for the main repo
    """
    dirty_submodules = []
    clean_repos = []
    main_repo = None
    dirty_submodule_paths = {}

    for repo in repos:
        path = repo["path"]
        is_submodule = repo.get("is_submodule", False)
        
        if has_changes(path):
            if is_submodule:
                dirty_submodules.append(repo)
                dirty_submodule_paths[repo["name"]] = path
            else:
                main_repo = repo
        else:
            if is_submodule:
                clean_repos.append(repo)
            else:
                main_repo = repo

    return dirty_submodules, clean_repos, main_repo, dirty_submodule_paths


def show_status(submodules: list[dict], main_repo: dict | None, repo_root: str):
    print("\n" + "="*50)
    print(f"{Colors.CYAN}Status of all repositories{Colors.NC}")
    print("="*50 + "\n")

    for sub in submodules:
        full_path = sub["path"]
        print(f"[submodule] {sub['name']}:")

        if not os.path.isdir(full_path):
            print(f"   {Colors.YELLOW}Directory not found{Colors.NC}")
            print("")
            continue

        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=full_path,
                capture_output=True,
                text=True,
            )
            branch = get_current_branch(full_path) or "(detached HEAD)"
            print(f"   Branch: {branch}")
            
            if result.stdout.strip():
                print(f"   {Colors.YELLOW}Status: Has changes{Colors.NC}")
                for line in result.stdout.strip().split("\n"):
                    print(f"      {line}")
            else:
                print(f"   {Colors.GREEN}Status: Working tree clean{Colors.NC}")
        except Exception as e:
            print(f"   {Colors.RED}Error: {e}{Colors.NC}")
        print("")

    if main_repo:
        print(f"[main] {main_repo['name']}:")
        try:
            branch = get_current_branch(main_repo["path"]) or "(detached HEAD)"
            print(f"   Branch: {branch}")
            
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=main_repo["path"],
                capture_output=True,
                text=True,
            )
            
            if result.stdout.strip():
                print(f"   {Colors.YELLOW}Status: Has changes{Colors.NC}")
                for line in result.stdout.strip().split("\n"):
                    print(f"      {line}")
            else:
                print(f"   {Colors.GREEN}Status: Working tree clean{Colors.NC}")
        except Exception as e:
            print(f"   {Colors.RED}Error: {e}{Colors.NC}")
    print("")


async def main():
    auto_commit = "-y" in sys.argv or "--yes" in sys.argv
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    root_path = find_script_git_root()

    print(f"{Colors.CYAN}╔{'═'*56}╗{Colors.NC}")
    print(f"{Colors.CYAN}║{' AI Git Commit (Deepiri) ':^56}║{Colors.NC}")
    print(f"{Colors.CYAN}╚{'═'*56}╝{Colors.NC}\n")

    print(f"{Colors.CYAN}Finding git repositories...{Colors.NC}")
    repos = find_git_repos(root_path)
    repos_with_changes = {r["path"]: True for r in repos if has_changes(r["path"])}

    if not repos:
        print(f"{Colors.RED}No git repositories found.{Colors.NC}")
        sys.exit(1)

    repos_with_changes_count = sum(1 for r in repos if r["path"] in repos_with_changes)
    print(f"\n{Colors.GREEN}Found {len(repos)} repository(ies) ({repos_with_changes_count} with changes):{Colors.NC}")
    for i, repo in enumerate(repos):
        markers = []
        if repo.get("is_submodule"):
            markers.append("submodule")
        if repo.get("is_sibling"):
            markers.append("sibling")
        marker_str = f" ({', '.join(markers)})" if markers else ""
        has_change = repo["path"] in repos_with_changes
        status = f" {Colors.YELLOW}●{Colors.NC}" if has_change else f" {Colors.GREEN}○{Colors.NC}"
        print(f"  {i + 1}) {repo['name']}{marker_str}{status}")
    print(f"  {len(repos) + 1}) (all)")
    print(f"  status) Show status of all repos")

    print(f"\n{Colors.CYAN}Select repositories to process (comma-separated, number for all):{Colors.NC}", end="")
    selection = input().strip().lower()

    if selection == "status":
        submodules = [r for r in repos if r.get("is_submodule")]
        main_repo = [r for r in repos if not r.get("is_submodule")]
        main = main_repo[0] if main_repo else None
        show_status(submodules, main, root_path)
        sys.exit(0)

    selected_repos = []
    dirty_submodules_to_process = []
    main_repo_to_process = None
    
    if selection == "all" or selection == str(len(repos) + 1) or selection == "a":
        repos_with_changes_list = [r for r in repos if r["path"] in repos_with_changes]
        
        if not repos_with_changes_list:
            print(f"\n{Colors.GREEN}No repositories have changes to commit.{Colors.NC}")
            sys.exit(0)
        
        print(f"\n{Colors.CYAN}Processing {len(repos_with_changes_list)} repo(s) with changes:{Colors.NC}")
        selected_repos = repos_with_changes_list
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",") if x.strip().isdigit()]
            selected_repos = [repos[i] for i in indices if 0 <= i < len(repos)]
        except ValueError:
            print(f"{Colors.RED}Invalid selection.{Colors.NC}")
            sys.exit(1)

    if not selected_repos:
        print(f"{Colors.RED}No repositories selected.{Colors.NC}")
        sys.exit(1)

    async with Spinner(f"Connecting to Ollama at {ollama_url}..."):
        models = await get_ollama_models(ollama_url)
    if models:
        print(f"  {Colors.GREEN}✔{Colors.NC} Ollama connected")

    if not models:
        print(f"{Colors.YELLOW}No models found in Ollama.{Colors.NC}")
        print(f"{Colors.RED}No models available.{Colors.NC}")
        sys.exit(1)

    if len(models) == 1:
        model = models[0]
        print(f"{Colors.GREEN}Using model: {model}{Colors.NC}\n")
    else:
        print(f"\n{Colors.GREEN}Available models:{Colors.NC}")
        for i, m in enumerate(models):
            print(f"  {i + 1}) {m}")
        print(f"\n{Colors.CYAN}Select model [1]: {Colors.NC}", end="")
        model_input = input().strip()

        if not model_input:
            model = models[0]
        elif model_input.isdigit() and 1 <= int(model_input) <= len(models):
            model = models[int(model_input) - 1]
        else:
            print(f"{Colors.RED}Invalid selection, using first model.{Colors.NC}")
            model = models[0]

        print(f"{Colors.GREEN}Using model: {model}{Colors.NC}\n")

    commit_all_remaining = False
    total_commits = 0
    skipped_commits = 0
    all_commits_made = []

    for repo in selected_repos:
        repo_path = repo["path"]
        repo_name = repo["name"]

        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.NC}")
        print(f"{Colors.MAGENTA}Repository: {repo_name}{Colors.NC}")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.NC}")

        diff_output = get_git_diff(repo_path)
        untracked = get_untracked_files(repo_path)

        if not diff_output and not untracked:
            print(f"{Colors.YELLOW}No changes in {repo_name}.{Colors.NC}")
            continue

        files = parse_changed_files(diff_output)

        submodule_pointers = {}
        for f in files:
            if f.get("is_submodule_pointer"):
                submodule_pointers[f["file"]] = {"old_sha": f["old_sha"], "new_sha": f["new_sha"]}

        known_submodule_paths = parse_gitmodules(repo_path)
        dirty_subs = get_dirty_submodules(repo_path, known_submodule_paths)
        for sub in dirty_subs:
            print(f"  {Colors.YELLOW}⚠{Colors.NC}  {sub['path']} has uncommitted changes "
                  f"({sub['modified']} modified, {sub['untracked']} untracked) — commit inside the submodule first")

        untracked_diffs = {}
        for upath in untracked:
            files.append({"file": upath, "hunks": [], "untracked": True})
            untracked_diffs[upath] = get_new_file_diff(repo_path, upath)

        if not files:
            print(f"{Colors.YELLOW}No files changed in {repo_name}.{Colors.NC}")
            continue

        total_files = len(files)
        print(f"  {Colors.CYAN}●{Colors.NC} {total_files} file(s) to commit\n")

        async with Spinner(f"Segmenting {total_files} files into commits...") as spinner:
            commit_plan = await analyze_and_segment_commits(
                base_url=ollama_url,
                model=model,
                repo_name=repo_name,
                diff_output=diff_output,
                files=files,
            )
        print(f"  {Colors.GREEN}✔{Colors.NC} Segmented into {len(commit_plan)} commit(s)")

        generated = []
        total = len(commit_plan)
        async with Spinner(f"[0/{total}] Generating commit messages...") as spinner:
            for i, commit in enumerate(commit_plan):
                files_to_commit = commit.get("files", [])
                spinner.update(f"[{i}/{total}] {', '.join(files_to_commit[:2])}{'...' if len(files_to_commit) > 2 else ''}")
                if not files_to_commit:
                    generated.append((commit, "", ""))
                    continue
                diff_snippet = extract_diff_for_files(diff_output, files_to_commit, untracked_diffs, submodule_pointers)
                subject, body = await generate_commit_message(
                    base_url=ollama_url,
                    model=model,
                    commit_description=commit.get("description", "Update"),
                    files=files_to_commit,
                    diff_snippet=diff_snippet,
                )
                generated.append((commit, subject, body))
        print(f"  {Colors.GREEN}✔{Colors.NC} Messages generated\n")

        print(f"{Colors.BOLD}{Colors.GREEN}Segmented into {len(generated)} commit(s):{Colors.NC}")
        for i, (commit, subject, _) in enumerate(generated):
            label = subject or commit.get("description", "No description")
            print(f"  {i + 1}) {label[:60]}")
            print(f"     Files: {', '.join(commit.get('files', [])[:5])}{'...' if len(commit.get('files', [])) > 5 else ''}")

        repo_auto_commit = auto_commit

        if not repo_auto_commit:
            print(f"\n{Colors.BLUE}[a] Auto-commit all  [r] Review each  [q] Quit: {Colors.NC}", end="")
            mode = input().strip().lower()
            if mode == "q":
                print(f"{Colors.YELLOW}Quitting...{Colors.NC}")
                sys.exit(0)
            repo_auto_commit = mode == "a"

        print(f"\n{Colors.CYAN}Starting commits...{Colors.NC}")

        for i, (commit, subject, body) in enumerate(generated):
            files_to_commit = commit.get("files", [])

            if not files_to_commit:
                print(f"{Colors.YELLOW}Skipping commit {i+1} - no files{Colors.NC}")
                skipped_commits += 1
                continue

            if repo_auto_commit or commit_all_remaining:
                confirmed = True
            else:
                confirmed = confirm_commit(repo_name, subject, body, files_to_commit, i + 1, len(generated))
                if confirmed == "commit_all":
                    commit_all_remaining = True
                    confirmed = True

            if confirmed:
                set_upstream_if_needed(repo_path)
                
                staged = stage_files(repo_path, files_to_commit)
                
                if staged:
                    committed = commit_changes(repo_path, subject, body)
                    
                    if committed:
                        print(f"{Colors.GREEN}✓ Committed: {subject[:50]}{Colors.NC}")
                        total_commits += 1
                        all_commits_made.append({
                            "repo": repo_name,
                            "subject": subject,
                            "body": body,
                            "files": files_to_commit,
                        })
                    else:
                        print(f"{Colors.RED}✗ Failed to commit{Colors.NC}")
                else:
                    print(f"{Colors.RED}✗ Failed to stage files{Colors.NC}")
            else:
                print(f"{Colors.YELLOW}⊘ Skipped commit {i+1}{Colors.NC}")
                skipped_commits += 1

    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.GREEN}Done!{Colors.NC}")
    print(f"  Commits created: {Colors.GREEN}{total_commits}{Colors.NC}")
    if skipped_commits > 0:
        print(f"  Skipped: {Colors.YELLOW}{skipped_commits}{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")

    if total_commits > 0 and all_commits_made:
        print(f"\n{Colors.BLUE}Generate PR description? [y/N]: {Colors.NC}", end="")
        if input().strip().lower() == "y":
            pr_desc = generate_pr_description(all_commits_made)
            
            print(f"\n{Colors.CYAN}{'─'*60}{Colors.NC}")
            print(f"{Colors.BOLD}PR Description (Deepiri Template){Colors.NC}")
            print(f"{Colors.CYAN}{'─'*60}{Colors.NC}\n")
            print(pr_desc)
            print(f"\n{Colors.CYAN}{'─'*60}{Colors.NC}")
            
            pr_output_dir = os.path.join(root_path, ".git", "ai-commit-output")
            os.makedirs(pr_output_dir, exist_ok=True)
            pr_file = os.path.join(pr_output_dir, "pr-description.md")
            with open(pr_file, "w") as f:
                f.write(pr_desc)
            print(f"\n{Colors.GREEN}✓ PR description saved to: {pr_file}{Colors.NC}")


if __name__ == "__main__":
    asyncio.run(main())
