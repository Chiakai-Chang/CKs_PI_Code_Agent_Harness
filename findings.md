# Findings

> External research, discoveries, constraints — written here, not in task_plan.md.

## User Analysis (from MECE discussion)

### P0: 新手試用者
- 很少碰終端
- 怕搞壞系統
- 只看 README 前 30 行
- 需要：一鍵、安全、可逆

### P1: 開發者，不熟悉 Pi
- 會 git clone、會裝 npm
- 怕環境污染
- 需要：明確、冪等、不髒系統

### P2: 熟手 / 貢獻者
- 懂 Pi、懂 harness
- 需要：靈活、可跳步驟、可 CI 集成

## Current Pain Points

1. **README too long** — P0 users overwhelmed; core CTA buried
2. **No trust statement** — users hesitant to run unknown scripts
3. **Dependency friction** — Git/Python/Node all required manually
4. **LLM config blocks flow** — no LLM = confused user
5. **No uninstall** — no reversibility = trust barrier
6. **No --auto mode** — CI/advanced users can't skip prompts
7. **No CI/Docker examples** — advanced users left guessing

## Technical Constraints

- Pi requires Node.js ≥ 20
- Pi installed via npm -g (may need admin)
- Skills/rules/extensions go to ~/.pi/agent/
- Local LLM scanning is best-effort (Ollama, LMStudio, etc.)
- Windows: Git Bash dependency, admin rights for npm -g
- Cross-platform: must support Win/macOS/Linux

## Trust Requirements (MECE)

| Element | Requirement |
|---------|-------------|
| Transparency | List exactly what script does |
| Verifiable | Code is open-source, auditable |
| Minimal privilege | Ask for admin only when needed |
| Reversible | Provide uninstall script |
| Open-source | MIT license, public repo |

## Design Decisions

- Design for P0, P1/P2 downward-compatible
- Non-blocking LLM config (don't stop if no LLM detected)
- Idempotent: running twice is safe
- Two modes: interactive (default) and --auto (CI/advanced)
