# 🧠 決策紀錄 (Rationale) - Environment Purifier (Self-Healing Reinstall)

## 1. 為什麼要引進環境淨化器 (Purifier)？
在「新電腦」或「多 Extensions 環境」場景下，AI 開發者常會面臨舊遺產 (Legacy Assets) 導致的衝突。引進 `purifier.py` 理由如下：
*   **消除環境雜訊**：舊有的擴充功能可能攔截新指令，或在路徑中產生無效的 Symlinks。
*   **資料安全繼承**：使用者通常不想重新設定 API Keys 或微調過後的手感。淨化器能智慧提取 `auth.json` 與 `models.json`。
*   **打造「零汙染」旗艦體驗**：確保旗艦版 v4.2 的九大支柱是在最純淨的底座上運行。

## 2. 為什麼選擇「備份優先 (Backup-First)」策略？
根據 `DISTILLATION_GUIDE.md` 的「環境自適應」原則：
*   **不可逆操作警告**：嚴禁靜默刪除使用者資料。所有舊環境均被移動至時間戳記備份目錄。
*   **高保真還原**：僅提取「核心配置（元數據）」，其餘「執行邏輯（舊 Extension）」則不予遷移，徹底斷開舊遺產的影響。

## 3. 核心價值：自癒力 (Self-Healing)
淨化器不僅是清理工具，它是本 Harness 的「免疫系統」。它讓本專案具備了「一鍵重生」的能力。

## 4. 維護計畫
*   持續更新 `essentials` 檔案列表，涵蓋未來可能出現的新配置（如 Anthropic 的全域設定）。

---
**本文件依據 $docs/core/DISTILLATION_GUIDE.md 建立，標誌著本 Harness 具備了工業級的環境容錯能力。**
