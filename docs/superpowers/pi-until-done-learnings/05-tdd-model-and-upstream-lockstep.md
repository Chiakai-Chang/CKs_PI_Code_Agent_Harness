# 收穫五：TDD 執行模型與上游版本鎖定自動化

> 來源：pi-until-done 的 phase discipline（SKILL.md）、AGENTS.md 繼承 pi-config operating contract、upstream lockstep workflow。
> 對應本專案：harness 開發工作流程、Pi 版本相容性管理。

## pi-until-done 的設計

### TDD-first 執行模型（寫入 SKILL.md，agent 每輪可見）
```
Every production-affecting goal MUST pass through these phases.
Declare your phase by passing `phase` to `until_done_progress`.

ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR

Constraints from pi-config:
  nesting depth ≤ 3, construct ≤ 30 LOC, file ≤ 200 LOC, single responsibility
```
- phase 是狀態的一部分（state.phase），工具 `until_done_progress` 宣告階段轉換
- 階段在 status line UI 可見 — 使用者可一瞥驗證紀律遵守
- 研究/文件目標可用 `phase: none` — 非所有工作都需 TDD

### pi-config Operating Contract（跨專案繼承）
- AGENTS.md 聲明 "adopts the pi-config operating contract in full" — 共享的開發合約倉庫定義 production code 邊界、TDD 紀律、自動化基礎設施
- Bootstrap status table 追蹤驗證基礎設施就緒狀態（canonical gate source、developer suite、release-readiness suite、affected-target execution）
- "If a more global AGENTS.md / CLAUDE.md conflicts with this file, **this file wins for this repo**" — 明確的優先序

### Upstream Lockstep Automation
- **确定性每日 workflow**：比較三個 `@earendil-works/pi-*` 套件最新版本，版本分歧 **fail closed**（不自動升級）
- 新精確匹配 release 觸發 sandboxed GitHub Agentic Workflow 修復相容性：
  - Grok 4.5 high reasoning 為主要修復模型
  - 三次嘗試、每次最多 16 Copilot continuations、合併 $5 AI credit ceiling + provider $25 monthly cap
  - **模型沙箱無 repository 或 publishing credential** — 安全邊界明確
  - repository-only GitHub App 做有限安全輸出
  - 最多 20 non-generated files、1,500 changed lines — 變更範圍上限
  - **immutable workflow/security/structure/package/Node contract tests** — 自動化本身被測試保護
  - GLM 5.2/xhigh review blocking extensions/** 變更 — 人工審查閘門

## 對應本專案的差距與改善空間

### 直接可用（中適用性）
1. **Pi 版本相容性追蹤**：pi-until-done 有 `compatibility/pi.json` 明確定義支援的 Pi 版本，每日自動化檢查分歧。我們的 harness 依賴特定 Pi API（ExtensionAPI、hooks）但無版本相容性記錄或自動化檢查 — 應至少文件化目前測試通過的 Pi 版本範圍。
2. **Bridge API import 來源分歧**（二次復盤已發現）：bridge 分用 `@mariozechner/pi-coding-agent` 與 `@earendil-works/pi-coding-agent` — pi-until-done 統一用 `@earendil-works/pi-*` 並鎖定精確版本。此問題應優先處理。

### 概念借鑑
- **Operating contract 繼承模式**：pi-config 作為共享合約倉庫被多個專案 AGENTS.md 引用 — harness 的 CLAUDE.md 原則可考慮此模式（但當前規模不需）。
- **Fail closed on version skew**：Pi 升級可能破壞 bridge API，自動升級風險高 — fail closed 是正確預設。

## pi-until-done 的實作細節
- AGENTS.md 定義 "production code" = `extensions/` 下運時代碼；tests/compatibility/ 不算
- mise.toml 為 canonical gate source，.github/workflows/ci.yml 鏡像它 — 單一真實來源
- 自動化 triage workflow 只有只讀權限（不能 comment/label/close issue），證據作為 Actions artifact 階段化供維護者本地審查後手動應用 — 防自動化濫用
