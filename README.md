# Daily Project & Git Digest (`daily-git-digest`)

An Antigravity skill and automated pipeline that audits Git commits, pull requests, and merges across repositories, produces structured daily markdown digests, and updates rolling release notes.

---

## 📁 Project Structure

```text
daily-git-digest/
├── SKILL.md                          # Antigravity skill specification (root copy)
├── README.md                         # Documentation and usage guide
├── .digest_state.json                # Tracks high-water mark commit and timestamp
├── .gitignore
├── .github/
│   └── workflows/
│       └── daily-digest.yml          # GitHub Actions scheduled workflow (00:00 UTC)
├── .agents/
│   └── skills/
│       └── daily-git-digest/
│           ├── SKILL.md              # Skill specification for Antigravity discovery
│           ├── scripts/
│           │   ├── digest_generator.py # Python CLI parser & digest generator
│           │   └── schedule_task.ps1   # Windows Task Scheduler automation script
│           ├── resources/
│           │   ├── digest_template.md        # Daily digest markdown template
│           │   └── release_notes_template.md # Rolling release notes template
│           └── references/
│               └── architecture.md   # Architectural patterns and reference
├── reports/                          # Generated daily digest reports (.md)
└── RELEASE_NOTES.md                  # Rolling release notes updated daily
```

---

## 🚀 Quick Start

### 1. Run Manually via Python
You can run the digest generator on any Git repository:

```powershell
python .agents/skills/daily-git-digest/scripts/digest_generator.py --repo-path "." --output-dir "reports" --update-release-notes
```

#### CLI Options:
* `--repo-path <path>`: Path to target git repository (defaults to current directory `.`).
* `--output-dir <path>`: Folder where daily reports are saved (defaults to `reports/`).
* `--days <int>`: Lookback window in days if no state file exists (defaults to `1`).
* `--since-last-run`: Use `.digest_state.json` to audit only new commits since the last run (enabled by default).
* `--update-release-notes`: Prepend features and bug fixes to `RELEASE_NOTES.md`.
* `--dry-run`: Output the generated Markdown to stdout without writing files.

---

## 🤖 Using with Antigravity

Because this skill is located at `.agents/skills/daily-git-digest/SKILL.md`, Antigravity will automatically discover it whenever this project (or any project you copy `.agents/` into) is your active workspace.

You can trigger it naturally by prompting:
> *"Generate today's git digest and update our release notes."*
> *"Audit git activity from the last 24 hours."*

---

## ⏰ Automated Daily Scheduling

### Option A: Windows Task Scheduler (Local Machine)
Use the included PowerShell utility to register a scheduled task that executes automatically every morning:

```powershell
# Register task to run daily at 9:00 AM
powershell -ExecutionPolicy Bypass -File .agents/skills/daily-git-digest/scripts/schedule_task.ps1 -Action Register -DailyTime "09:00"

# Check status of scheduled task
powershell -ExecutionPolicy Bypass -File .agents/skills/daily-git-digest/scripts/schedule_task.ps1 -Action Status

# Run immediately
powershell -ExecutionPolicy Bypass -File .agents/skills/daily-git-digest/scripts/schedule_task.ps1 -Action RunNow

# Unregister / remove scheduled task
powershell -ExecutionPolicy Bypass -File .agents/skills/daily-git-digest/scripts/schedule_task.ps1 -Action Unregister
```

### Option B: GitHub Actions (CI/CD)
The workflow at `.github/workflows/daily-digest.yml` runs every midnight UTC on GitHub Actions, audits commits from the past 24 hours, generates the report, and commits the updates back to your repository with `[skip ci]`.

---

## 🛠️ Operational Reference & Commands

| Objective | Method | Command / Action |
| :--- | :--- | :--- |
| **Check Local Task Status** | PowerShell | `powershell -ExecutionPolicy Bypass -File .agents\skills\daily-git-digest\scripts\schedule_task.ps1 -Action Status` |
| **Trigger Immediate Local Run** | Python CLI | `python .agents/skills/daily-git-digest/scripts/digest_generator.py --repo-path "." --output-dir "reports" --update-release-notes` |
| **Trigger Remote Cloud Run** | GitHub CLI | `gh workflow run daily-digest.yml` |
| **View Cloud Action Runs** | GitHub CLI | `gh run list --workflow=daily-digest.yml` |
| **Unregister Local Task** | PowerShell | `powershell -ExecutionPolicy Bypass -File .agents\skills\daily-git-digest\scripts\schedule_task.ps1 -Action Unregister` |

