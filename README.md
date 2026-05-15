# 🚀 CK's Universal Code Agent Harness (Flagship v4.0)

> **一鍵重建工業級 AI 開發環境** —— 為您的 AI 助手 (Claude, Codex, Gemini) 注入全球頂尖專家的開發直覺與嚴謹紀律。

`CK's Universal Code Agent Harness` 是一個專為 **AI 命令行工具** (如 [Claude Code](https://github.com/anthropic/claude-code), [Pi Gemini](https://github.com/badlogic/pi-mono)) 打造的**旗艦級配置增強套件**。本專案透過「適配器模式 (Adapter Pattern)」與「智慧映射 (Smart Mapping)」技術，整合了 GitHub 15+ 個頂尖開源倉庫，實現了「一套核心，多端投影」。

---

## 🏗️ 九大技術支柱 (The 9 Pillars)

基於 [**核心設計理念 (CORE_CONCEPTS.md)**](docs/core/CORE_CONCEPTS.md) 與 [**v4.0 投影導則**](docs/core/DISTILLATION_GUIDE.md)，我們構建了跨平台的開發大腦：

1.  **🛡️ 紀律守護 (Universal Hooks)**：整合 80+ 專業代理人與自動化掛鉤，在 AI 闖禍前（如語法錯誤、金鑰洩漏）秒級攔截，支援 Bash 與 Edit 掛鉤映射。
2.  **🧠 專家直覺 (Superpowers)**：注入工業級工程紀律，強制 AI 實施 TDD 與系統化規劃，工具名自動隨平台轉譯。
3.  **🔍 代碼 GPS (Understand)**：利用知識圖譜技術，讓 AI 具備解讀數萬行複雜專案的「上帝視角」。
4.  **📚 專案大腦 (LLM Wiki)**：實作 Karpathy 模式，讓專案知識隨時間複利成長，建立持久的維基索引。
5.  **📝 戰術持久 (Manus Planning)**：實體化任務計畫，確保跨對話斷點續傳，徹底解決長對話導致的 AI 「失憶」問題。
6.  **🏭 代理工廠 (OMC Teams)**：建立多代理編排流水線，召喚架構師、執行者與審查員協同作戰，適配多平台指令集。
7.  **🧪 誠信工廠 (AIxBDD)**：實施嚴格的行為驅動開發 (BDD)，確保代碼與規格 100% 對齊。
8.  **🧬 自我進化 (Evolver Engine)**：基於 GEP 協定，將成功修復固化為「基因」，實現跨會話的能力遺傳。
9.  **🧭 產品決策 (PM Skills)**：內建 100+ 頂尖 PM 框架，從北極星指標到 PRD 審計，以「圖書館模式」按需調度。

> ℹ️ 每一項整合的技術細節與決策背景，請參閱 [**🗺️ 戰略索引地圖 (STRATEGIC_MAP.md)**](docs/strategy/STRATEGIC_MAP.md)。

---


## 📂 整合生態系 (Integrated Masterpieces)

本專案透過 Git Submodule 連結以下大師級資產，確保與上游 100% 同步：

| 領域 | 來源專案 / 大師 | 賦予 Pi 的核心神力 |
| :--- | :--- | :--- |
| **工程紀律** | [ECC](https://github.com/affaan-m/everything-claude-code) | 自動品質門檻、安全審查、50+ 特種代理人。 |
| **方法論** | [Superpowers](https://github.com/obra/superpowers) | TDD 驅動、系統化規劃、專家選擇直覺。 |
| **行為準則** | [Karpathy](https://github.com/forrestchang/andrej-karpathy-skills) | 鎖定 Andrej Karpathy 觀察的 LLM 避坑開發指南。 |
| **認知提取** | [Nuwa (女媧)](https://github.com/alchaincyf/nuwa-skill) | **專家工廠**：內建 15 位名家（賈伯斯、芒格等）思維框架。 |
| **TS 專家** | [Matt Pocock](https://github.com/mattpocock/skills) | 宏觀架構導航、深模組化重構、TypeScript 深度偵錯。 |
| **Web 權威** | [Addy Osmani](https://github.com/addyosmani/agent-skills) | Google 級效能審計、API 契約設計、懷疑驅動開發 (DDD)。 |
| **提示工程** | [Prompt Master](https://github.com/nidhinjs/prompt-master) | 提示詞自動壓縮與跨模型指令翻譯，極致節省 Token。 |
| **CLI 標準** | [Printing Press](https://github.com/mvanhorn/cli-printing-press) | 實施 **CK-Spec-01** 標準，打造 Agent-Native 精簡輸出。 |
| **BDD 專家** | [AIxBDD](https://github.com/Waterball-Software-Academy/aixbdd) | **誠信工廠**：RED-GREEN-REFACTOR 閉環、需求變更自動調和。 |
| **能動性守護** | [PIP Guardian](https://github.com/tanweai/pua) | **生產力改進**：4 級壓力升級、14 種大廠方法論、拒絕偷懶。 |
| **代理工廠** | [OMC](https://github.com/Yeachan-Heo/oh-my-claudecode) | **多代理編排**：32+ 專業角色、Sisyphus 持久化、團隊模式。 |
| **安全治理** | [YES.md](https://github.com/sstklen/yes.md) | **六層防禦**：Anti-Slack 偵測、機器強制 Hooks、安全閘門。 |
| **視覺美學** | [Taste Engine](https://github.com/Leonxlnx/taste-skill) | **視覺指揮官**：三旋鈕參數控制、反 AI 罐頭化、極致性能。 |
| **產品決策** | [PM Skills](https://github.com/phuryn/pm-skills) | **戰略圖書館**：100+ 頂尖 PM 框架、北極星指標、需求審計。 |
| **自我進化** | [Evolver](https://github.com/EvoMap/evolver) | **基因優化**：掃描失敗模式、固化抗體基因、實現長期成長。 |

---

## 🚀 快速上手 (Quick Start)

### 1. 取得專案
```bash
git clone --recursive https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
cd CKs_PI_Code_Agent_Harness
```

### 2. 一鍵適配
*   **Windows**: 雙擊 `install.bat` (建議管理員執行)。
*   **macOS / Linux**: `bash install.sh`。

> 系統會自動執行 **Universal Mapping**，偵測系統中安裝的 `claude` 或 `pi` 指令，並動態投影專家大腦。

### 3. 開始開發
*   **Claude Code**: `claude`
*   **Gemini CLI**: `pi`
*   **Codex CLI**: `codex`

---

## 🛠️ 核心規格與自豪功能

*   **⚡ Map-Driven Restore**：完全捨棄散裝複製，改用智慧映射，支援全域絕對路徑定位。
*   **🧠 Context Kernel**：內建「上下文內核協議」，自動管理注意力預算，長對話中 Token 經濟提升 40%。
*   **🧠 Hippocampus (海馬迴)**：整合 `hello-reflect`，自動從您的修正中學習並更新 `CLAUDE.md`。
*   **🕵️ Stealth Force**：選配整合 `camofox-stealth`，具備繞過 Cloudflare 偵測的頂級隱身瀏覽力。
*   **📑 Rationale Archive**：每一項整合都有專屬的 `RATIONALE.md`，決策背景透明、戰略脈絡可追溯。

---

## ✅ 隱私、安全與信任

*   **本地優先**：針對 Ollama / llama.cpp 優化，代碼與智慧資產不出門。
*   **安全攔截**：內建 ECC 防火牆，防止 AI 意外刪除 `.env` 或推送金鑰。
*   **完全開源**：從腳本到 Prompts，一切透明。

---

## 🙏 感謝與授權

*   本專案採用 **MIT 授權**。
*   向所有在「整合清單」中出現的開源大師致敬，你們的智慧是本專案的靈魂。

---
**由 [CK (Chiakai Chang)](https://github.com/Chiakai-Chang) 維護，旨在打造最強適應力的 AI 開發環境。**

