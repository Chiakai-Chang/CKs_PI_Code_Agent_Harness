# MECE-Autopilot Agent Mandate

Quick reference for AI agents working with MECE-Autopilot.

---

## 📜 Core Mandate

**Read [CONSTITUTION.md](CONSTITUTION.md) for full principles and protocol.**

---

## 🔧 Setup

| Platform | Skill | Decisions |
|----------|-------|----------|
| Claude Code | `skills/mece-autopilot/SKILL.md` | `decisions/` |
| Gemini CLI | `skills/mece-autopilot/SKILL.md` | `decisions/` |
| Universal | — | `decisions/` |

---

## 📋 Quick Reference

- **Activate (Inline Mode)**: `/mece-autopilot <problem>` (Runs debate inline within the active agent session)
- **Orchestrator Mode (Recommended for L2/L3)**:
  - Initialize: `./mece-autopilot "Problem description"` (macOS/Linux) or `.\mece-autopilot.ps1 "Problem description"` (Windows)
  - Step forward: `./mece-autopilot --step` or `.\mece-autopilot.ps1 --step`
  - Interactive CLI: `./mece-autopilot` or `.\mece-autopilot.ps1`
- **Constitution**: [CONSTITUTION.md](CONSTITUTION.md)
- **Skill**: [skills/mece-autopilot/SKILL.md](skills/mece-autopilot/SKILL.md)
- **Quality Example**: [reference/examples/L2_standard-mece.md](reference/examples/L2_standard-mece.md)
- **Track Decision**: Append to `decisions/_registry.md`

---

## 🔄 Commit Workflow

**Before committing, ensure:**

1. ✅ **CHANGELOG.md** updated (if feature/fix)
2. ✅ **decisions/_registry.md** updated (if new decision)
3. ✅ **wiki/log.md** updated (if MECE-Autopilot session completed)
4. ✅ **VERSION.md** updated (if version bump)

**Commit format:**
```
type(scope): subject

body (optional)

Ref: [decision-id]
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `style`, `test`, `chore`
**Scopes:** `core`, `docs`, `decisions`, `wiki`, `skills`, `config`, `all`

**Quick commit (developers only):**
```bash
# First, install dev tools (one-time)
git clone https://github.com/Chiakai-Chang/mece-autopilot.git && cd mece-autopilot
cp -r dev/hooks .git/hooks/

# Then use
./dev/scripts/commit-helper.sh <type> <scope> "subject"
```

**Detailed guide (developers only)**: [dev/COMMIT_WORKFLOW.md](dev/COMMIT_WORKFLOW.md)

---

**Last Updated**: 2026-07-03

