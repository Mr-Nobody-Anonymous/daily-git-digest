#!/usr/bin/env python3
"""
Daily Git & Project Digest Generator
Extracts git commits, categorizes by conventional commit conventions,
computes code metrics, generates markdown daily digests, and updates release notes.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple


STATE_FILE = ".digest_state.json"
DEFAULT_REPORTS_DIR = "reports"
DEFAULT_RELEASE_NOTES = "RELEASE_NOTES.md"

CATEGORIES = [
    ("features", "🚀 Features & Enhancements", [r"^feat(\(.*\))?:", r"^feature(\(.*\))?:"]),
    ("fixes", "🐛 Bug Fixes", [r"^fix(\(.*\))?:", r"^bugfix(\(.*\))?:", r"^hotfix(\(.*\))?:"]),
    ("docs", "📚 Documentation", [r"^docs?(\(.*\))?:"]),
    ("refactor", "♻️ Refactoring & Performance", [r"^refactor(\(.*\))?:", r"^perf(\(.*\))?:", r"^style(\(.*\))?:"]),
    ("tests", "🧪 Tests & Coverage", [r"^tests?(\(.*\))?:"]),
    ("chores", "🔧 Maintenance & Chores", [r"^chore(\(.*\))?:", r"^build(\(.*\))?:", r"^ci(\(.*\))?:"]),
    ("merges", "🔀 Merges & Pull Requests", [r"^Merge\s+"]),
]


def run_git(args: List[str], cwd: str) -> str:
    """Run a git command and return its stdout as a string."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace"
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return ""


def get_repo_name(repo_path: str) -> str:
    """Determine the name of the repository."""
    toplevel = run_git(["rev-parse", "--show-toplevel"], repo_path)
    if toplevel:
        return os.path.basename(os.path.abspath(toplevel))
    return os.path.basename(os.path.abspath(repo_path))


def get_current_branch(repo_path: str) -> str:
    """Get the current active branch."""
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)
    return branch or "main"


def get_current_head_hash(repo_path: str) -> str:
    """Get full HEAD hash."""
    return run_git(["rev-parse", "HEAD"], repo_path)


def load_state(repo_path: str) -> Dict:
    """Load the state file if it exists."""
    state_path = os.path.join(repo_path, STATE_FILE)
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(repo_path: str, head_hash: str) -> None:
    """Update state file with the latest run info."""
    state_path = os.path.join(repo_path, STATE_FILE)
    state = load_state(repo_path)
    state["last_run_timestamp"] = datetime.datetime.now().isoformat()
    state["last_commit_hash"] = head_hash
    state["digests_generated_count"] = state.get("digests_generated_count", 0) + 1
    
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_commit_range(repo_path: str, days: int, use_state: bool) -> Tuple[Optional[str], Optional[str]]:
    """Determine commit revision range or time constraint."""
    if use_state:
        state = load_state(repo_path)
        last_hash = state.get("last_commit_hash")
        if last_hash:
            # Check if last_hash still exists in repo
            check = run_git(["rev-parse", "--quiet", "--verify", last_hash], repo_path)
            if check:
                current_head = get_current_head_hash(repo_path)
                if check == current_head:
                    return None, "NO_NEW_COMMITS"
                return f"{last_hash}..HEAD", None

    since_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d 00:00:00")
    return None, since_date


def fetch_commits(repo_path: str, rev_range: Optional[str], since_date: Optional[str]) -> List[Dict]:
    """Fetch and parse commit records."""
    delimiter = "---RECORD-DELIMITER---"
    field_delim = "%x1f"
    fmt = f"%h{field_delim}%H{field_delim}%an{field_delim}%ad{field_delim}%s{delimiter}"
    
    args = ["log", f"--format={fmt}", "--date=iso-strict"]
    if rev_range:
        args.append(rev_range)
    elif since_date:
        args.append(f"--since={since_date}")

    raw_output = run_git(args, repo_path)
    if not raw_output:
        return []

    commits = []
    records = raw_output.split(delimiter)
    for record in records:
        record = record.strip()
        if not record:
            continue
        parts = record.split("\x1f")
        if len(parts) >= 5:
            commits.append({
                "short_hash": parts[0].strip(),
                "full_hash": parts[1].strip(),
                "author": parts[2].strip(),
                "date": parts[3].strip(),
                "subject": parts[4].strip(),
            })
    return commits


def categorize_commits(commits: List[Dict]) -> Tuple[Dict[str, List[Dict]], List[Dict]]:
    """Group commits into conventional commit categories."""
    categorized = {cat[0]: [] for cat in CATEGORIES}
    other_commits = []

    for commit in commits:
        subj = commit["subject"]
        matched = False
        for cat_key, _, patterns in CATEGORIES:
            for pattern in patterns:
                if re.search(pattern, subj, re.IGNORECASE):
                    categorized[cat_key].append(commit)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            other_commits.append(commit)

    return categorized, other_commits


def fetch_diff_stats(repo_path: str, rev_range: Optional[str], since_date: Optional[str]) -> Dict[str, str]:
    """Get overall diff statistics."""
    args = ["diff", "--shortstat"]
    if rev_range:
        args.append(rev_range)
    elif since_date:
        args.append(f"@{{{since_date}}}")
        args.append("HEAD")

    stat = run_git(args, repo_path)
    if not stat:
        return {"files_changed": "0", "insertions": "0", "deletions": "0"}

    # Example: " 3 files changed, 45 insertions(+), 12 deletions(-) "
    files = re.search(r"(\d+)\s+file", stat)
    ins = re.search(r"(\d+)\s+insertion", stat)
    dels = re.search(r"(\d+)\s+deletion", stat)

    return {
        "files_changed": files.group(1) if files else "0",
        "insertions": ins.group(1) if ins else "0",
        "deletions": dels.group(1) if dels else "0",
    }


def generate_digest_markdown(
    repo_name: str,
    branch: str,
    commits: List[Dict],
    categorized: Dict[str, List[Dict]],
    other: List[Dict],
    stats: Dict[str, str],
    date_str: str,
) -> str:
    """Format the digest into structured Markdown."""
    authors = sorted(list(set(c["author"] for c in commits)))

    md = []
    md.append(f"# 📅 Daily Project & Git Digest: {repo_name}")
    md.append(f"**Date:** {date_str} | **Branch:** `{branch}` | **Total Commits:** {len(commits)}\n")

    md.append("## 📊 Executive Metrics")
    md.append("| Metric | Count |")
    md.append("| :--- | :--- |")
    md.append(f"| **Commits Audited** | {len(commits)} |")
    md.append(f"| **Active Contributors** | {len(authors)} ({', '.join(authors) if authors else 'None'}) |")
    md.append(f"| **Files Changed** | {stats['files_changed']} |")
    md.append(f"| **Lines Added / Removed** | +{stats['insertions']} / -{stats['deletions']} |")
    md.append("")

    if not commits:
        md.append("> [!NOTE]\n> No commits recorded in the audited period. Repository is up to date.\n")
        return "\n".join(md)

    # Categories
    has_deliverables = False
    for cat_key, cat_title, _ in CATEGORIES:
        items = categorized.get(cat_key, [])
        if items:
            has_deliverables = True
            md.append(f"### {cat_title}")
            for c in items:
                md.append(f"- [`{c['short_hash']}`] **{c['subject']}** — *{c['author']}*")
            md.append("")

    if other:
        md.append("### 📦 Other Changes")
        for c in other:
            md.append(f"- [`{c['short_hash']}`] {c['subject']} — *{c['author']}*")
        md.append("")

    md.append("---")
    md.append("*(Report automatically generated by `daily-git-digest` skill)*")
    return "\n".join(md)


def update_release_notes(repo_path: str, date_str: str, categorized: Dict[str, List[Dict]]) -> None:
    """Prepend or update daily highlights in RELEASE_NOTES.md."""
    rn_path = os.path.join(repo_path, DEFAULT_RELEASE_NOTES)
    features = categorized.get("features", [])
    fixes = categorized.get("fixes", [])

    if not features and not fixes:
        return

    new_section = [f"### [{date_str}] Daily Rollup"]
    if features:
        new_section.append("#### Features")
        for f in features:
            new_section.append(f"- {f['subject']} ({f['short_hash']})")
    if fixes:
        new_section.append("#### Bug Fixes")
        for fix in fixes:
            new_section.append(f"- {fix['subject']} ({fix['short_hash']})")
    new_section.append("")
    section_text = "\n".join(new_section) + "\n"

    if os.path.exists(rn_path):
        with open(rn_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Insert after top title if exists
        lines = content.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("# "):
                insert_idx = i + 1
                break
        lines.insert(insert_idx, "\n" + section_text)
        with open(rn_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    else:
        with open(rn_path, "w", encoding="utf-8") as f:
            f.write(f"# Release Notes\n\n{section_text}")


def main():
    parser = argparse.ArgumentParser(description="Generate a daily Git digest report.")
    parser.add_argument("--repo-path", default=".", help="Path to git repository root.")
    parser.add_argument("--output-dir", default=DEFAULT_REPORTS_DIR, help="Directory to save digest reports.")
    parser.add_argument("--days", type=int, default=1, help="Lookback window in days (default: 1).")
    parser.add_argument("--since-last-run", action="store_true", default=True, help="Use state file for incremental audit.")
    parser.add_argument("--update-release-notes", action="store_true", help="Prepend highlights to RELEASE_NOTES.md.")
    parser.add_argument("--dry-run", action="store_true", help="Print report to stdout without writing files.")

    args = parser.parse_args()
    repo_path = os.path.abspath(args.repo_path)

    # Check git repo
    is_git = run_git(["rev-parse", "--is-inside-work-tree"], repo_path)
    if is_git != "true":
        print(f"Error: '{repo_path}' is not a valid git repository.", file=sys.stderr)
        sys.exit(1)

    repo_name = get_repo_name(repo_path)
    branch = get_current_branch(repo_path)
    head_hash = get_current_head_hash(repo_path)
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")

    rev_range, since_date = get_commit_range(repo_path, args.days, args.since_last_run)

    if since_date == "NO_NEW_COMMITS":
        print(f"Notice: No new commits since last digest run ({head_hash[:8]}).")
        return

    commits = fetch_commits(repo_path, rev_range, since_date)
    categorized, other = categorize_commits(commits)
    stats = fetch_diff_stats(repo_path, rev_range, since_date)

    digest_content = generate_digest_markdown(
        repo_name=repo_name,
        branch=branch,
        commits=commits,
        categorized=categorized,
        other=other,
        stats=stats,
        date_str=now_date,
    )

    if args.dry_run:
        print(digest_content)
        return

    # Write report file
    out_dir = os.path.join(repo_path, args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    report_filename = f"daily-digest-{now_date}.md"
    report_path = os.path.join(out_dir, report_filename)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(digest_content)

    print(f"✅ Generated daily digest: {report_path}")

    if args.update_release_notes:
        update_release_notes(repo_path, now_date, categorized)
        print(f"✅ Updated release notes: {os.path.join(repo_path, DEFAULT_RELEASE_NOTES)}")

    save_state(repo_path, head_hash)
    print("✅ State persisted to .digest_state.json")


if __name__ == "__main__":
    main()
