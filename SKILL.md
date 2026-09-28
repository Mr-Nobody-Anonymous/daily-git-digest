---
name: daily-git-digest
description: >-
  Audits git commits, pull requests, and branch activity across a repository,
  produces structured daily markdown digests, and updates rolling release notes.
  Use this skill when the user asks for a daily git digest, commit audit,
  project changelog rollup, or automated daily repository status reporting.
---

# Daily Project & Git Digest Skill

This skill teaches the agent how to perform deterministic, automated daily audits of any Git repository. It extracts changes, groups commits by conventional types, highlights contributors, records diff statistics, and updates rolling release notes while maintaining incremental state.

## Core Capabilities

1. **Incremental & Date-Range Auditing**: Automatically inspects changes since the last run recorded in `.digest_state.json`, or defaults to the last 24 hours.
2. **Conventional Commit Categorization**: Parses and organizes commits into Features, Fixes, Docs, Refactoring, Performance, and Chores.
3. **Contributor & Diff Analytics**: Aggregates unique authors, lines added/removed, and modified files.
4. **Rolling Release Notes Update**: Appends summarized daily highlights to `RELEASE_NOTES.md` and updates `CHANGELOG.md`.
5. **Self-Auditing & State Maintenance**: Records high-water mark commit hashes to guarantee idempotent and gapless reporting.

---

## Directory Structure & Resources

```text
daily-git-digest/
├── SKILL.md                          # This instruction runbook
├── scripts/
│   ├── digest_generator.py           # Core CLI parser & markdown generator
│   └── schedule_task.ps1             # Windows Task Scheduler automation helper
├── resources/
│   ├── digest_template.md            # Daily digest markdown template
│   └── release_notes_template.md     # Rolling release notes structure
└── references/
    └── architecture.md               # Continuous automation & self-audit reference
```

---

## Step-by-Step Procedure

When triggered by the user (or invoked through an automated script):

### Step 1: Detect Repository Context and High-Water Mark

1. Verify that the target working directory is a Git repository:
   ```powershell
   git rev-parse --is-inside-work-tree
   ```
2. Locate or read `.digest_state.json` in the project root:
   - If present: Extract `last_commit_hash` and `last_run_timestamp`.
   - If missing: Default to looking back 1 day (`git log --since="24 hours ago"`).

### Step 2: Extract and Categorize Changes

Run the bundled generator script to parse commits, diff statistics, and merge pull requests:

```powershell
python .agents/skills/daily-git-digest/scripts/digest_generator.py --repo-path "." --output-dir "reports" --update-release-notes
```

Alternatively, if performing manual agent inspection:
- **Commits query**:
  ```powershell
  git log --since="1 day ago" --pretty=format:"%h%x09%an%x09%ad%x09%s" --date=short
  ```
- **Diffstat summary**:
  ```powershell
  git diff --shortstat "@{1 day ago}" HEAD
  ```
- **Merges & PRs**:
  ```powershell
  git log --merges --since="1 day ago" --pretty=format:"%h %s (%an)"
  ```

### Step 3: Format the Daily Digest Markdown

Store the output in `reports/daily-digest-YYYY-MM-DD.md`.
Ensure the digest includes:
- **Header**: Date, repository name, branch, audited commit range (`HEAD~N..HEAD`).
- **Executive Summary**: 2-3 sentence overview of major changes.
- **Key Deliverables (Features & Fixes)**: Categorized list with commit links/hashes and authors.
- **Maintenance & Chores**: Build, refactoring, documentation, tests.
- **Contributor Activity**: Authors active during the reporting period.
- **Repository Metrics**: Commits count, files changed, insertions/deletions.

### Step 4: Update Rolling Release Notes

If `--update-release-notes` is enabled or requested:
1. Check if `RELEASE_NOTES.md` exists. If not, initialize it using `resources/release_notes_template.md`.
2. Prepend or update the entry for the current date under the unreleased / active milestone section.
3. Keep entries human-readable, prioritizing user-facing features and critical fixes over internal chores.

### Step 5: Self-Audit & State Persistence

1. Inspect the generated digest file to ensure no empty sections or parsing artifacts.
2. Update `.digest_state.json` with:
   - `last_run_timestamp`: Current ISO 8601 timestamp.
   - `last_commit_hash`: Current `HEAD` revision hash.
   - `digests_generated_count`: Incremented total.
3. Report a concise summary to the user with a clickable markdown link to the new digest.

---

## Automation & Scheduling Options

To run this skill continuously without manual initiation, consult [architecture.md](./references/architecture.md):

* **Windows Task Scheduler (Local)**:
  Run `powershell -ExecutionPolicy Bypass -File .agents/skills/daily-git-digest/scripts/schedule_task.ps1 -Action Register -DailyTime "09:00"` to schedule a daily unattended run.
* **GitHub Actions (CI/CD)**:
  Use `.github/workflows/daily-digest.yml` to run the digest on a daily cron (`schedule: - cron: '0 0 * * *'`) and commit the report or post an issue summary.
