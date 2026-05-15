# RATIONALE: addyosmani/agent-skills 整合決策理由書

## 1. 決策背景
*   **來源專案**：https://github.com/addyosmani/agent-skills
*   **核心功能**：由 Google Chrome 團隊領導者 Addy Osmani 打造的高階 Web 工程工作流（效能優化、API 設計、遷移策略）。
*   **評估日期**：2026-05-13

## 2. 戰略分析 (Technical SWOT/TOWS)
*   **S (優勢)**：具備 Google 級別的效能優化與架構廣度。引入「懷疑驅動開發 (DDD)」有效抑制 AI 幻覺。
*   **W (劣勢)**：部分基礎技能與現有框架重疊，全量開啟會導致提示詞臃腫。
*   **O (機會)**：補完本 Harness 在「複雜系統重構」與「頂級 Web 效能審計」領域的空缺。

根據 **v3.7 導則**，這屬於 **SO 策略區間**：利用全球頂尖專家的資產，將 Pi 的 Web 工程上限拉高至產業標竿。

## 3. 最終決策：🟢 Path 1 (原生映射 - 精選)
理由如下：
1.  **維護性優先**：Addy Osmani 的方法論會隨瀏覽器技術與 Web 標準演進，原生映射可確保我們始終享有最新的 Google 級別實踐。
2.  **專業深度**：其 `/api-design` 與 `/performance-optimization` 提供了極高保真度的工業標準，不應進行簡化蒸餾。
3.  **依賴隔離**：僅映射精選技能，將其餘資產保留在 `external/` 目錄，兼顧強大功能與輕量核心。

## 4. 實施清單 (Curated Selection)
挑選了具備最高差異化價值的 6 項技能：
1.  **performance-optimization**：專業的 Web 效能審計與優化建議。
2.  **doubt-driven-development**：強制 AI 進行懷疑性推理，防止錯誤的自動化決策。
3.  **api-and-interface-design**：高品質、一致性的 API 契約設計。
4.  **deprecation-and-migration**：處理大型專案的舊功能棄用與新架構遷移。
5.  **documentation-and-adrs**：產出具備架構脈絡的決策紀錄 (ADRs)。
6.  **browser-testing-with-devtools**：利用 DevTools 進行深度自動化測試。

---
**本文件依據 DISTILLATION_GUIDE v3.7 規範存檔。**
