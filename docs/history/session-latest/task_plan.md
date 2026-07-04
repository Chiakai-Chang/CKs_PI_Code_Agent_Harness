# One-Click Onboarding — Task Plan

> **Goal:** 讓「跨平台、未安裝 Pi、不想複雜設定」的用戶，
> 用最少步驟、最低心理門檻，一鍵順利體驗 Pi + 本專案 Skills。
>
> **Method:** 10-round MECE expert roundtable → concrete implementation plan.

## Status: DONE — P0 merged to main

## Phases

### Phase 1: Context & Documentation ✅
- [x] 10-round MECE expert discussion (8 roles)
- [x] one-click-onboarding-design.md
- [x] one-click-implementation-plan.md (high-level)
- [x] task_plan.md (this file)
- [x] findings.md
- [x] progress.md
- [x] Commit + push

### Phase 2: Detailed Implementation Plan (writing-plans style)
- [x] Write TDD-style implementation plan:
  - docs/superpowers/plans/2025-05-06-one-click-onboarding.md
  - Each task: exact files, exact tests, exact code, exact commands
- [x] Self-review plan

### Phase 3: Execute via Subagent-Driven Development
- [ ] Create feature branch
- [ ] Dispatch subagents per task (2-stage review)
- [ ] Final code review
- [ ] Use finishing-a-development-branch skill

## Tasks (High-Level)

Derived from MECE discussion. Will be broken down into TDD-style tasks in Phase 2.

| # | Task | Priority | Status |
|---|------|----------|--------|
| T1 | README 重構（3分鐘快速開始 + 信任檢查清單） | 🔴 P0 | ✅ done |
| T2 | install.bat 改進（信任聲明 + 進度 + 冪等） | 🔴 P0 | ✅ done |
| T3 | setup.py 改進（--auto 模式 + LLM 友善提示） | 🔴 P0 | ✅ done |
| T4 | 新增 uninstall.py | 🔴 P0 | ✅ done |
| T5 | install.sh 改進（對稱 install.bat） | 🔴 P0 | ✅ done |
| T6 | Windows GUI 安裝器（setup.exe） | 🟡 P1 | pending |
| T7 | macOS/Linux 一鍵腳本（brew bundle / apt） | 🟡 P1 | pending |
| T8 | CI / Docker 範例 | 🟡 P1 | pending |
| T9 | 可攜式 Pi Harness（願景） | 🟢 P2 | pending |
| T10 | Web-based 安裝嚮導（願景） | 🟢 P2 | pending |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| (none yet) | - | - |
