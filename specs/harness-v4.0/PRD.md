# 📄 產品需求文件 (PRD) - Universal Harness v4.0

## 1. 產品願景
讓本 Harness 成為 AI 開發者的「萬能插座」。無論使用者選擇哪種 AI CLI 工具，都能立即獲得全球頂尖專家的開發紀律、審美與流程。

## 2. 目標對象
*   在 Claude Code、Gemini CLI 與 Codex CLI 之間切換的專業開發者。
*   希望在一套規則下維持開發一致性的開發團隊。

## 3. 核心需求 (User Stories)
*   **US-1**: 作為一個開發者，我希望能在 `git clone` 後執行 `setup`，系統自動幫我設定好當前正在使用的 AI 平台。
*   **US-2**: 作為一個架構師，我希望定義一次規則（如 `coding-style.md`），這份規則能同時被 Claude 和 Gemini 識別。
*   **US-3**: 作為一個工程師，我希望跨平台的工具差異（如 `replace` vs `Edit`）由 Harness 層自動調和。

## 4. 驗收標準 (Acceptance Criteria)
*   [ ] **多平台支援**：Harness 必須能同時生成並映射 `.gemini/`, `.claude/`, `.codex/` 需要的元數據檔案。
*   [ ] **指令統一**：使用者輸入相同的指令（如 `/team`），在不同平台都能觸發對應的邏輯。
*   [ ] **環境自癒**：若切換平台，執行 `restore` 應能自動清理舊平台的映射並建立新平台的連結。

---
**版本：Flagship v4.0-Draft**
