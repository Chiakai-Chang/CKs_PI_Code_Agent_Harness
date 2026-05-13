# PRD: Flagship Setup & Configuration System v3.7.2

## 1. 核心願景 (Core Vision)
建立一個具備「工業級穩定性」與「智慧自適應能力」的一鍵式環境恢復系統。

## 2. 業務目標 (Business Objectives)
*   **零摩擦部署**：新用戶或換電腦時，3 分鐘內恢復 100% 戰力。
*   **硬體主權**：精準偵測 RAM/VRAM，不因語系或環境變量導致 `??GB` 報錯。
*   **真值主權**：100% 尊重本地 LLM 服務 (llama.cpp/Ollama) 的物理極限，杜絕 AI 硬編碼覆蓋。

## 3. 功能需求 (Functional Requirements)
*   **啟動器 (Bootstrapper)**：`.bat`/`.sh` 僅負責偵測 Python 與提權，核心邏輯下放 `setup.py`。
*   **互動菜單**：支援 [1] 完整安裝、[2] 切換模型、[3] 還原配置。
*   **智慧探針 (The Probes)**：
    *   **RAM/VRAM**：支援多重編碼 (UTF-16, CP65001) 解析，具備 PowerShell Fallback。
    *   **API Truth**：同時嗅探 `/props` 與 `/slots`，提取真正的 `n_ctx`。
*   **規格推薦 (Recommendation Engine)**：
    *   **優先權 1**：API 實測真值（Found Truth）。
    *   **優先權 2**：硬體防禦限制（向下修正以防崩潰）。
    *   **優先權 3**：基於模型尺寸的啟發式推薦（僅在無真值時）。
*   **自癒同步**：自動處理 Git Submodule 與 `safe.directory` 信任。

## 4. 非功能需求 (Non-Functional Requirements)
*   **代碼完備性**：禁止功能退化，所有 Helper 函式必須完整保留。
*   **跨平台性**：路徑處理統一使用 `os.path.join` 與 `replace("\\", "/")`。
*   **編碼一致性**：內部傳輸統一使用 UTF-8，與 Windows 系統通訊使用動態偵測。
