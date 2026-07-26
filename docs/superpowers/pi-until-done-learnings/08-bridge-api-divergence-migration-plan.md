# Bridge API Import 來源分歧：發現與遷移計畫

> 二次復盤（11-review）已標記此問題；本文記錄實查證據與遷移步驟。
> 狀態：**調查完成，遷移待 Pi 運行時測試驗證**。

## 發現

本 harness 的 9 個 bridge 的 `ExtensionAPI` import 來自兩個不同 npm 套件：

| 套件 | 最新版本 | 最後更新 | 性質 | 使用的 bridge |
|---|---|---|---|---|
| `@mariozechner/pi-coding-agent` | 0.73.1 | 2026-05-07 | oh-my-pi fork，已凍結 | case-bridge、ecc-hooks-bridge、mece-autopilot-bridge、planning-with-files-bridge、taste-bridge |
| `@earendil-works/pi-coding-agent` | 0.82.1 | 2026-07-25 | 原始 Pi 上游，活躍 | compact-continuation-bridge、skill-namespace-guard、stealth-web-bridge |

**版本差距超過 5 個月、9 個次要版本**。settings.json `lastChangelogVersion: 0.73.0` 表明 harness 最初構建於 Pi 0.73.x 時代，較新的 bridge 改用上游套件。

## 實查證據

- npm registry 確認：`@mariozechner/pi-coding-agent` 最新 0.73.1（2026-05-07），之後無發布；`@earendil-works/pi-coding-agent` 最新 0.82.1（2026-07-25）。
- ecc-hooks-bridge 使用 `import { isToolCallEventType } from "@mariozechner/pi-coding-agent"` — **已實查確認**：該函數存在於上游套件的主要導出（npm 0.82.1 的 dist/index.d.ts 第 8 行有 export），遷移無此障礙。
- pi-until-done（srinitude，Pi 核心貢獻者）統一用 `@earendil-works/pi-*` 並鎖定精確版本（compatibility/pi.json: Pi 0.81.1）。

## 風險評估

- **隱蔽分歧風險**：兩套件的 ExtensionAPI 型別定義可能已分歧，但 bridge 編譯通過（Pi 的 TypeScript 編譯在 Pi 運行時環境中，非本 repo 本地）— 問題可能在運行時才暴露。
- **目前無已知運行時故障報告**：bridge 在實際使用中被觀察到運作，但不排除未觸發的邊緣路徑有分歧。

## 遷移步驟（需 Pi 運行時測試驗證）

1. **確認型別定義差異**：比對兩套件 `@types` 或聲明文件中 ExtensionAPI、hook event 型別、`pi.registerTool`/`pi.sendMessage` 簽名的差異。重點檢查 ecc-hooks-bridge 依賴的 `isToolCallEventType` 是否在上游存在。
2. **統一 import 來源**：將 5 個 bridge 的 import 改為 `@earendil-works/pi-coding-agent`。
3. **加 peerDependency 版本鎖定**：各 bridge package.json 加 `"peerDependencies": { "@earendil-works/pi-coding-agent": ">=0.74.0 <0.83.0" }`（範圍覆蓋已知運作版本到當前上游），並記錄於 bridge-manifest.json。
4. **Pi 運行時測試**：在實際 Pi session 中驗證每個遷移後的 bridge 功能（hook 觸發、工具註冊、訊息發送）— 此步驟不可省略，遵循「實測有證據」原則。
5. **更新 compatibility/pi.json**（若 harness 採用 pi-until-done 的精確版本鎖定模式）。

## 阻塞條件

遷移的步驟 4（Pi 運行時測試）需要 Pi 安裝環境與實際 session 測試 — 無法在本 repo 的 git/bash/Python 工具鏈中完成。此項標記為「調查完成，遷移待驗證」而非直接執行，避免無驗證的 API 變更。
