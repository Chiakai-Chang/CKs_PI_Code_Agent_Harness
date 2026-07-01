# 🧠 決策紀錄 (Rationale) - Graphify Bridge

## 1. 為什麼要引進 Graphify？
對於超大型程式庫，AI 代理在回答「架構關係、模組調用、全域數據流」等高層級問題時，直接閱讀或檢索所有原始代碼檔案會耗費天價的 Token，且容易引發 Context 窗口溢出。
引進 `safishamsi/graphify` 的核心目的在於：
*   **代碼關係圖譜化 (Code Graph Extraction)**：利用 AST (樹分析器 `tree-sitter`) 提取出明確的調用 (calls)、引用 (uses) 與導入 (imports) 關係。
*   **大幅節省 Token (71.5x token efficiency)**：代理查詢關係圖譜與 Community 結構，而非生啃數百個原始代碼文件。
*   **本地無縫運行與可視化**：不需外部重型向量資料庫，可導出為 Obsidian Vault 或是啟動為 Stdio MCP Server 供 Agent 即時查詢。

---

## 2. 與既有大腦系統 (LLM Wiki & understand-knowledge) 的關係與協同

我們目前已導入 `praneybehl/llm-wiki-plugin` (專案大腦) 以及 `pi-skills/core/understand-knowledge`。它們與 `graphify` 的定位及邊界如下：

```text
               +-------------------------------------------+
               |         CK's Pi Project Brain             |
               +----------------------+--------------------+
                                      |
             +------------------------+------------------------+
             |                                                 |
   [ 語法結構腦 (Graphify) ]                         [ 語義知識腦 (LLM Wiki) ]
   - 提取自：程式碼 AST (Tree-sitter)                - 提取自：LLM 沉澱的設計決策、筆記與 Schema
   - 特性：自動化、客觀、精準結構                     - 特性：手動/LLM 編譯、富有業務脈絡與意圖
   - 表現：graphify-out/ (GRAPH_REPORT.md)           - 表現：wiki/ (index.md + markdown)
             |                                                 |
             +------------------------+------------------------+
                                      |
                     [ 互補整合：Graphify 內置規則 ]
                     "If wiki/index.md exists, navigate it
                      instead of reading raw files"
```

### ➔ 擇一還是各取優點？
**兩者是完美的互補關係，完全不需擇一，應各取優點融合使用：**
1.  **結構化與代碼層面 (Graphify 優勢)**：程式碼的進出調用關係（AST）、SQL 綱要的引用，這些是客觀且結構極其複雜的關係。交由 `graphify` 透過樹語法分析器**零成本自動提取**，能徹底杜絕 LLM 對程式碼架構的幻覺。
2.  **決策與語義層面 (LLM Wiki 優勢)**：產品需求 (PRD)、業務核心約束、架構決策原因（ADR）、不寫在代碼裡的商業邏輯，這些主觀意圖交由 `llm-wiki` **在每次實踐復盤時沉澱**。
3.  **聯動運作**：Graphify 的引導規則中明文規定，如果 `wiki/index.md` 存在，Agent 查詢時應優先導航維基，這形成了「**語義大腦指導宏觀方向，語法圖譜保證微觀精準**」的雙引擎架構。

---

## 3. 戰略整合路徑：SO + WO 混合策略 (子模組 + 本地 Rules + 零依賴保護)
根據 `DISTILLATION_GUIDE.md`：
1.  **原生映射 (Path 1)**：引進子模組 `external/graphify`，註冊 `graphify-code` 技能。
2.  **零依賴防禦 (WO 策略)**：
    *   `graphify` 所需的 Python 重型依賴（如 `faster-whisper` 等）**不應**在 restore 時強制全域安裝，避免污染主機並導致 restore 失敗。
    *   在 [restore.py](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/scripts/restore.py) 中僅處理資料夾映射與 path-patch，並在 `best-practices` 等地方引導用戶「若要激活 graphify，可手動執行 `pip install graphifyy`」。
3.  **規則蒸餾**：在 [AGENTS.md](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/pi-rules/AGENTS.md#L30) 中，已將其「查閱 `GRAPH_REPORT.md` 定位 god nodes」與「主動更新 `graphify update` 避免大腦過期」的核心引導寫入系統規則。
