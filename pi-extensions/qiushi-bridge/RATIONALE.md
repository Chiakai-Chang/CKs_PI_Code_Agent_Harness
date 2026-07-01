# 🧠 決策紀錄 (Rationale) - Qiushi Skill Bridge

## 1. 為什麼要引進 qiushi-skill？
當面對極其複雜的除錯、架構重構或系統整合任務時，AI Agent 常見的失控模式是「胡子眉毛一把抓」，缺乏主次之分。
引進 `qiushi-skill` 是為了提供一套結構化的認知框架：
*   **主要矛盾定位 (Contradiction Analysis)**：分析開發過程中的互相牽制，明確取捨，抓住問題的牛鼻子。
*   **實踐認識論 (Practice-Cognition)**：強調「實踐→認識→再實踐」的循環，與 TDD (Test-Driven Development) 的紅綠燈循環完美吻合。
*   **集中兵力 (Concentrate Forces)**：在資源（Token/Context）受限時，引導 Agent 暫時停下其他支線，專攻主要阻塞點。

---

## 2. 為什麼選擇「原生映射 (Native Mapping)」+「輕量橋接」？
根據 `DISTILLATION_GUIDE.md`：
*   **SO 策略 (發揮優勢/利用機會)**：`qiushi-skill` 的所有專家技能均以標準 Markdown (SKILL.md) 格式存放，且具備優秀的中英雙語觸發描述。因此最適路徑是 **Submodule 直接原生映射（Path 1）**。
*   **橋接整合**：在 `pi-extensions/qiushi-bridge` 中建立極簡的映射 JSON 設定，將矛盾分析、實踐認識等核心技能註冊進 Pi Engine，確保無縫調用。

---

## 3. 未來維護計畫
*   定期同步 `external/qiushi-skill` 獲取最新的認知架構與工作流範例。
