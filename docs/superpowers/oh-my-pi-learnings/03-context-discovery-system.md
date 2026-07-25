# oh-my-pi 學習筆記：統一情境檔案發現系統

> 來源：`reference/oh-my-pi/docs/context-files.md`、`packages/coding-agent/src/discovery/*`

## 核心機制

oh-my-pi 自動發現並注入多套 agent 工具的情境檔案，無需使用者手動指示：

### 提供者層級與優先順序
| 優先序 | 提供者 | 路徑範例 |
|---:|---|---|
| 100 | `native` | `.omp/AGENTS.md`、`~/.omp/agent/AGENTS.md` |
| 80 | `claude` | `.claude/CLAUDE.md` |
| 70 | `agents` / `codex` | `.agents/AGENTS.md`、`.codex/AGENTS.md` |
| 60 | `gemini` | `.gemini/GEMINI.md` |
| 55 | `opencode` | `.config/opencode/AGENTS.md` |
| 30 | `github` | `.github/copilot-instructions.md` |
| 10 | `agents-md` | 獨立 `AGENTS.md`（非 config 目錄） |

### 發現規則
- **向上行走**：從 cwd 向上一路走到 repo root，最近的非空 `.omp/` 勝出（祖先層級不疊加）
- **按深度去重**：同深度的不同提供者取優先序高者；不同深度的檔案可共存
- **位元相同內容合併**：多份完全相同的內容只保留最靠近 cwd 的副本
- **排序**：遠祖檔案排在前面，靠近 cwd 的排在後面（更醒目）

### Sticky Rules vs Context
- `AGENTS.md` 作為 `<context>` 區塊注入開場情境，隨對話增長可能滑出注意力範圍
- `RULES.md` 轉為 always-apply rule，在當前回合附近重新附加，長對話中保持約束力

## 對本專案的啟發

### 直接可用
- **Bridge 註冊驗證**：我們的 `settings.json` 註冊了 5 個 extensions + 5 個 skills，但無任何優先序或衝突解析機制。若兩個 bridge 提供同名 skill，行為未定義。應引入提供者優先序系統。
- **情境檔案發現**：我們依賴 Pi 內建的 `.agents/AGENTS.md` 和 `CLAUDE.md` 發現。可考慮採用 oh-my-pi 的向上行走 + 深度去重邏輯，確保 monorepo 子專案的情境正確層疊。
- **Sticky Rules 概念**：我們的 `pi-rules/AGENTS.md` 作為 Pi 規則注入，但長對話中可能被遺忘。可將最關鍵的約束（實測有證據、方法論優先）抽離為 sticky rule 格式。

### 概念借鑑
- **提供者抽象化**：oh-my-pi 用統一 `DiscoveryProvider` 介面處理多套 agent 工具的檔案發現，而非硬編碼路徑列表。我們的 bridge 系統可採用類似模式，讓新增外部 skill 來源只需註冊一個 provider。
- **位元相同合併**：避免重複內容佔用情境空間，對 token 經濟很重要。

### 改善空間（oh-my-pi 自身）
- `.omp/` 目錄必須非空才參與行走 — 空目錄被跳過，可能讓使用者困惑為何祖先檔案未被發現。
- `SYSTEM.md` / `APPEND_SYSTEM.md` 不支援向上行走（只在 cwd 和 user 層級查找），與 `AGENTS.md` 行為不一致。
