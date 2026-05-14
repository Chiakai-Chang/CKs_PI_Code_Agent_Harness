# 🧠 決策紀錄 (Rationale) - YES Governance Bridge

## 1. 為什麼要引進 YES.md？
`sstklen/yes.md` 是一個高品質的 AI 治理框架。整合理由如下：
*   **結構化治理**：提出了「六層治理機制」，從 Prompt 到實體腳本 (Hooks) 全方位約束 AI 行為。
*   **Anti-Slack (抗偷懶)**：精準打擊 AI 常見的「推託使用者」、「未經驗證的歸因」與「只說不做」等惡習。
*   **安全攔截 (Safety Gates)**：提供實體腳本如 `pre-bash-guard.sh`，在 AI 執行危險指令（如 `rm -rf`）前進行強制攔截。

## 2. 為什麼選擇「原生映射 (Native Mapping)」+「輕量橋接 (Thin Bridge)」路徑？
根據 `DISTILLATION_GUIDE.md`，我們採取混合模式：
*   **原生映射 (Skills)**：其核心技能檔案（尤其是 `yes-zh/SKILL.md`）結構純淨，直接 Submodule 引進可享有上游的持續優化。
*   **輕量橋接 (Hooks)**：其原生的 Shell Hooks 針對 Unix 設計，本 Bridge 將其邏輯映射至本 Harness 的 `scripts/` 環境中，並與現有的 `ECC Hooks` 協作。

## 3. 核心價值：安全防線 (Safety Shield)
本 Bridge 為本 Harness 建立了一套「防護罩」。它與 `PIP Guardian` (壓力型) 形成互補：`YES.md` 提供明確的正確路徑與結構，確保 AI 助手在極限執行時依然保持誠信與安全。

## 4. 維護計畫
*   定期執行 `git submodule update --remote` 以拉取最新的治理規則。
*   持續監控其安全攔截邏輯與 Windows 環境的相容性。

---
**本文件依據 $docs/core/DISTILLATION_GUIDE.md 建立。**
