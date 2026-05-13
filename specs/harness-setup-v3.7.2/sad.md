# SAD: Setup v3.7.2 Architecture & Domains

## 1. 領域模型 (Domain Model - DDD)

### A. Environment Domain (環境領域)
*   **責任**：Git/Python/Node 可用性檢查。
*   **關鍵邏輯**：`has_command`, `suggest_git/node`, `init_git_harness`。

### B. Hardware Domain (硬體領域)
*   **責任**：實體資源感知。
*   **關鍵邏輯**：`get_hardware_info`, `run` (Multi-encoding)。
*   **實體**：`RAM`, `VRAM`。

### C. LLM Probe Domain (偵測領域)
*   **責任**：探尋本地服務真值。
*   **關鍵邏輯**：`probe_ollama`, `probe_llama_cpp`, `fetch_ollama_metadata`, `fetch_llamacpp_metadata` (Props/Slots)。

### D. Spec Domain (規格領域)
*   **責任**：參數平衡與推薦。
*   **核心規則**：Truth-First. `get_recommended_specs`。

### E. Orchestration Domain (編排領域)
*   **責任**：流程控制與 UI 呈現。
*   **核心組件**：`main`, `show_main_menu`, `run_restore` (calling restore.py)。

## 2. 數據流 (Data Flow)
`Input` -> `Hardware Probe` + `API Probe` -> `Recommendation Logic (Truth-Aware)` -> `User Approval` -> `JSON Sync` -> `Restore`.

## 3. 工業級安全防線 (Quality Gates)
*   **Encoding Gate**：`run()` 必須具備三階編碼嘗試。
*   **Path Gate**：寫入 `models.json` 必須經過路徑斜線正規化。
*   **Truth Gate**：如果 `found_truth` 為真，推薦值必須鎖定為實測值。
