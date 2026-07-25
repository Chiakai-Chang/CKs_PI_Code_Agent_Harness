# 二次復盤：當前狀態評估與其他可參考專案

> 對 oh-my-pi 學習後優化工作的再檢查，加上其他 AI coding agent/harness 專案的適用性評估。

## 一、當前優化工作的再檢查

### 已妥善處理的項目 ✅
- **Bridge manifest + verify-bridges.py**：9 bridges 全部入口路徑存在，交叉比對正確區分 package.json 註冊 vs Pi-runtime settings.json 載入
- **validate-config.py**：schema 驗證、機器路徑偵測（修正 JSON escape trap bug）、金鑰模式偵測（修正 sk-ant- 前綴匹配 bug）— 兩項 bug 經實測驗證已修復
- **skill-namespace-guard 升級**：跨來源衝突報告寫入 pi-config/skill-conflict-report.json，Pi 運行時碰撞處理邏輯不變
- **external-manifest.json**：20 個外部來源統一記錄（修正 agi-super-team 類型為 orphaned-clone）

### 發現但未修復的實際問題 ⚠️
1. **Bridge API 來源不一致**：經檢查，9 個 bridge 的 ExtensionAPI import 來自兩個不同套件：
   - `@mariozechner/pi-coding-agent`（oh-my-pi fork 套件名）：case-bridge、ecc-hooks-bridge、mece-autopilot-bridge、planning-with-files-bridge、taste-bridge
   - `@earendil-works/pi-coding-agent`（原始 Pi 套件名）：compact-continuation-bridge、skill-namespace-guard、stealth-web-bridge
   - **風險**：兩套件 API 可能已分歧，但 bridge 無版本鎖定或相容性驗證。此為前置問題非本次引入。

2. **Pi 原生功能未充分利用**（詳見下文 nunorralves 文章收穫）

3. **external/agi-super-team/** 殘留目錄與 scripts/verify_agi_super_team.sh 未處理 — manifest 已標記 orphaned-clone，清理需人工決策

## 二、從 nunorralves「Pi Extensions: Deep Lifecycle Integration」學到的關鍵點

來源：[nunorralves.pt/posts/2026-06-08-pi-extensions](https://www.nunorralves.pt/posts/2026-06-08-pi-extensions) — 這是目前最深入的 Pi 擴充機制實務文章，直接適用於本 harness。

### 核心設計哲學
> "A skill can describe what Pi should do. An extension can control what Pi actually does."
> "My rule of thumb: start with a skill. When it breaks — when the LLM misinterprets a branch, when you need a confirm dialog, when you're writing curl commands as instructions instead of making HTTP calls directly — extract the fragile part into an extension."

### 本 harness 可立即借鑑的改進
1. **Pi 原生事件系統更豐富**：我們的 bridge 只用 `resources_discover`，但 Pi 還有 `tool_call`（可用 `{block:true}` 攔截）、`before_agent_start`（動態修改 system prompt）、`tool_result`（轉換/過濾工具輸出）、`session_start`。oh-my-pi 的 hook 系統設計可對照理解 Pi 原生事件的生命週期位置。
2. **Pi Packages 是原生分享機制**：npm 描述明言 "Put your extensions, skills... in Pi Packages and share via npm or git"，用 `package.json` 的 `pi.extensions` 欄位註冊。本 harness 用 bridge 資料夾 + settings.json 手動註冊重現了此模式，但未採用 Pi 原生的 package 分發模型。
3. **Skills vs Extensions 決策框架**：我們的 harness 同時使用 skill（SKILL.md）和 extension（bridge），但缺少「何時用哪種」的明確指導文件。nunorralves 的決策矩陣（需攔截/需 API 呼叫/需 TUI → extension；純語言指令/可靠度可接受 → skill）可直接化為本 harness 的貢獻指南。
4. **API 限制與地雷**：無 `before_skill_load` 事件（解釋為何 skill-namespace-guard 必須在 `resources_discover` 運作）；`ctx.newSession()/fork()/reload()` 只能在 command handler 呼叫，event handler 中呼叫會靜默 deadlock — 此警告應文件化。

### 適用性評估
nunorralves 文章的價值不在提供新工具，而在揭示 **Pi 平台自身的能力邊界與最佳實踐** — 這是 harness 設計的上游參考，重要性不亞於 oh-my-pi 的架構洞察。oh-my-pi 教我們「如何建健康的管理層」，此文教我們「在 Pi 平台上什麼該用原生能力、什麼才需要 bridge」。

## 三、其他可參考專案評估

搜尋範圍：AI coding agent harness/framework 開源專案（排除完整 agent 本身如 claude-code、cursor）。

### Agentrail (yai-dev/agentrail)
- **定位**：「open-source agent harness framework for building, hosting, and orchestrating tool-using AI agents」— 與本 harness 同為 harness 層，但面向不同使用者
- **架構亮點**：組合式核心（@agentrail/core）、託管伺服器層（@agentrail/app）、提示 SDK、多 agent 編排、檔案系統記憶、沙箱執行、外掛/工作流程
- **適用性：低**。Agentrail 是「從零建構 agent 的 harness」，本專案是「增強既有 Pi agent 的配置層」。兩者解決不同問題；Agentrail 的多 agent 編排和託管伺服器與本 harness 無關。其 npm 套件化分發模式（@agentrail/capabilities 等）概念上類似 Pi Packages，但 API 不互通。

### Goose (aaif-goose/goose)
- **定位**：完整開源 AI agent（install, execute, edit, test with any LLM）
- **適用性：低**。這是 agent 本身非 harness 層；其 extensible 設計可能未來影響 Pi 生態，但當前無直接可借鑑的 harness 模式。

### 結論：oh-my-pi + nunorralves 文章已覆蓋本 harness 的主要參考需求
- oh-my-pi 提供 **harness 管理層** 的設計典範（完整性驗證、提供者優先序、寫入前驗證）
- nunorralves 文章提供 **Pi 平台能力邊界** 的實務地圖（事件系統、skill/extension 決策、API 限制）
- 其他專案要麼是完整 agent（不同層級），要麼是建構 agent 的 harness（不同目標），無直接適用模式

## 四、下一步建議（按優先序）

| 項目 | 來源 | 緊急度 | 範圍 |
|---|---|---|---|
| 文件化 Skills vs Extensions 決策框架 | nunorralves | 中 | pi-rules/ 或 CONTRIBUTING.md |
| 統一 bridge API import 來源並加版本鎖定 | 本次復盤發現 | 中 | 需確認兩套件 API 是否真分歧 |
| 探索 Pi Packages 分發模型替代 settings.json 手動註冊 | nunorralves + npm 描述 | 低 | 結構性變更，需測試 |
| 清理 external/agi-super-team 殘留 | manifest 標記 | 低 | 人工決策 |
