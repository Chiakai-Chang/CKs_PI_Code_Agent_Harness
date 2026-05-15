---
name: cua-commander
description: 連接本地已安裝的 cua (Computer Use Agent) 服務。僅在您已安裝 Docker/QEMU 並啟動 cua 服務時使用。此技能提供指令範本，讓 Pi 成為 cua 服務的「指揮中心」。
---

# /cua-commander

> **注意**：本專案不內建 `cua`。請確保您已依照 [trycua/cua](https://github.com/trycua/cua) 官方文件完成安裝。

## 核心功能
本技能將 Pi 轉化為 cua 的前端指揮官。當您需要執行以下操作時請調用：
*   「請打開瀏覽器幫我註冊一個帳號」
*   「請幫我測試這個 App 的登入 UI」

## 使用方式
1.  **啟動服務**：在您的終端機啟動 `cua server`。
2.  **指令對接**：Pi 會透過 Bash 工具調用 `cua-cli` 執行任務。
3.  **視覺反饋**：Pi 將讀取 cua 生成的截圖日誌來評估執行結果。

## 運作準則
*   **權力隔離**：Pi 僅負責發號施令，所有的重型運算與虛擬化操作由外部 cua 承擔。
*   **環境保持**：若偵測到環境中無 `cua` 指令，請優雅地提醒用戶先安裝，不要嘗試自行下載 heavy binaries。
