# 🚀 One-Click Onboarding Design — Expert Roundtable (MECE)

> 目標：讓「跨平台、未安裝 Pi、不想複雜設定」的用戶，
> 用最少步驟、最低心理門檻，安全且順利地體驗 Pi + 本專案 Skills。
>
> 方法：MECE 角色模擬討論，多輪窮盡，直到收文。

---

## 👥 參與角色

| 角色 | 關注焦點 |
|------|----------|
| PM（產品經理） | 用戶分群、核心旅程、成功指標 |
| UX 設計師 | 心理門檻、認知負荷、信任感 |
| DevOps/SRE | 可靠性、冪等、邊界案例、回滾 |
| 安全工程師 | 信任、透明、最小權限、審計 |
| CLI/前端設計師 | 終端體驗、視覺回饋、訊息清晰度 |
| 跨平台工程師（Win/macOS/Linux） | 平台差異、路徑、權限、Shell |
| 可及性/包容性倡議者 | 非技術用戶、低資訊素養、語言 |
| 進階用戶/貢獻者代言人 | 進階需求、可定制、不被過度引導 |

---

## Round 1：問題定義與用戶分群

### PM
核心問題：
> 「一個完全沒用過 Pi 的人，看到 GitHub 頁面後，從 0 到『pi 跑起來 + skills 生效』，最短多快？心理上多安全？」

用戶分群（MECE）：

- P0：新手試用者
  - 特徵：很少碰終端、怕搞壞系統、只看 README 前 30 行
  - 需求：一鍵、安全、可逆
- P1：開發者，但不熟悉 Pi
  - 特徵：會 git clone、會裝 npm、怕環境污染
  - 需求：明確、冪等、不髒系統
- P2：熟手 / 貢獻者
  - 特徵：懂 Pi、懂 harness
  - 需求：靈活、可跳步驟、可 CI 集成

**結論：以 P0 為設計基準，P1/P2 向下兼容。**

### UX 設計師
P0 的心智模型：
- 「一鍵」= 一個動作 → 完成
- 「可信」= 知道會做什麼、為什麼要這樣做
- 「安全」= 不會偷偷裝奇怪東西
- 「可逆」= 後悔可以撤

**設計準則：**
- 一鍵入口：單一檔案，單一指令
- 明確告知：「這會安裝 X、Y、Z，佔用約 W MB」
- 可逆：提供 uninstall / cleanup 指令
- 避免：技術黑話、大段指令、手動複製貼上

---

## Round 2：前置依賴（Git / Python / Node / Pi）

### 跨平台工程師
問題：
- 目前：要求 Git + Python + Node 都已存在 → 對 P0 不友善
- 理想：一鍵腳本自動處理，或提供極簡安裝器

MECE 拆解：

| 依賴 | 現況 | 風險 | 建議 |
|------|------|------|------|
| Git | 需手動裝 | 新手不知道 Git 是什麼 | 提供 winget / brew / apt 一鍵提示；或改用 GitHub Desktop（GUI） |
| Python | 需手動裝 | 版本衝突 | 建議 3.10+；Windows 用 winget；macOS 用 brew |
| Node ≥ 20 | 需手動裝 | 權限問題、nvm 複雜 | 提供 nvm 指引；或考慮 bundling |
| Pi | npm 全域安裝 | npm -g 權限問題 | 腳本自動安裝，但提示「這會安裝 pi 命令」 |

### DevOps/SRE
關鍵原則：
- 冪等：跑兩次不爆炸
- 失敗可恢復：每一步都有明確錯誤訊息 + 下一步建議
- 不偷偷改系統：每個安裝都需確認

**建議：**
- 加入「自動模式」與「互動模式」
  - 自動模式（--auto）：合理預設，適合 CI/熟手
  - 互動模式（預設）：每一步詢問，適合 P0/P1

### UX 設計師
P0 最怕：
- 一堆終端文字飛過，看不懂
- 突然要求管理員權限
- 安裝完不知道「到底成不成功」

**要求：**
- 開頭一屏：說明「這支腳本要做什麼」
- 每個階段：用圖示簡短說明（✅❌⚠️）
- 結尾一屏：成功畫面 + 下一步指令

### 安全工程師
- 全域安裝（npm -g）需：
  - 明確告知
  - 解釋「為什麼」
  - 不預設 y
- 腳本不應：
  - 偷偷下載不明來源
  - 修改系統環境變數（除非用戶同意）

**建議：**
- 顯示「信任檢查清單」：
  - 本腳本只做 X、Y、Z
  - 不收集資料
  - 不呼叫外部伺服器（除 npm 和 Pi 官方來源）

### PM（收文）
針對依賴的 MECE 策略：

- 階段 1（立即可做）：
  - 改善 install.bat / install.sh：
    - 加入「信任說明」
    - 更友善的錯誤訊息
    - 自動模式選項
- 階段 2（中短期）：
  - 提供「平台專屬一鍵安裝器」：
    - Windows: setup.exe（bundled Python + Node 檢查）
    - macOS: 使用 brew bundle
    - Linux: 使用 apt / dnf / pacman 自動判斷
- 階段 3（長期）：
  - 考慮打包為可攜式版本（Portable Pi Harness）：
    - 內建 Node + Python，不污染系統

---

## Round 3：一鍵入口設計

### CLI 前端設計師
設計目標：
- 用戶只需「看到一個連結 + 一個指令」就能開始
- 終端體驗像「互動式嚮導」

**方案 A（推薦，短期）：增強版 install.bat / install.sh**

- 開頭顯示：
  ```
  ============================================
    CK's Pi Code Agent Harness
    一鍵安裝 AI 程式開發助手
  ============================================

  這支腳本會：
    1. 檢查 Git / Python / Node.js
    2. 安裝 Pi（AI 助手核心）
    3. 套用開發 Skills 與規則
    4. 掃描你的本地 LLM（Ollama 等）

  不會：
    - 收集個人資料
    - 呼叫外部追蹤 API
    - 修改系統環境變數

  來源：
    GitHub: https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness

  是否繼續？(y/N):
  ```

- 加入進度提示：
  - [1/6] 檢查環境...
  - [2/6] 安裝 Node.js（若未安裝）
  - [3/6] 安裝 Pi...
  - [4/6] 掃描 LLM...
  - [5/6] 套用配置...
  - [6/6] 完成！

**方案 B（中期）：平台專屬安裝器**

- Windows:
  - 提供 setup.exe（用 NSIS / Inno Setup 打包）
  - 內建：
    - Git 檢查（若無，使用 winget）
    - Python 檢查
    - Node 檢查
    - Pi 安裝
    - 配置還原
  - 圖形化進度條
  - 一鍵完成

- macOS:
  - 使用 Homebrew Bundle（Brewfile）
  - 或提供 .pkg 安裝器

- Linux:
  - 提供 install-ubuntu.sh / install-fedora.sh
  - 或通用版自動偵測套件管理器

### UX 設計師
P0 用戶旅程（目標）：

1. 看到 GitHub README
2. 看到「快速開始」區：
   - 一句話：「3 分鐘內體驗 AI 開發助手」
   - 一個指令：`git clone ... && cd ... && .\install.bat`
   - 一個連結：「看不懂？看這個圖文教程」
3. 執行後：
   - 看到清晰的進度
   - 沒有令人困惑的提示
4. 最後：
   - 「✅ 安裝完成！輸入 pi 即可開始使用」
   - 附上簡單驗證指令

### DevOps/SRE
冪等與邊界案例：

- 若 Pi 已安裝 → 提示「是否更新？」
- 若 skills 已存在 → 提示「是否覆蓋？」
- 若路徑已存在 → 備份後覆蓋
- 若網路不佳 → 明確顯示錯誤，不崩潰
- 所有步驟冪等：跑兩次不爆炸

### PM（收文）
一鍵入口策略：

- 短期（立即可做）：
  - 改善 install.bat / install.sh（加入信任提示 + 進度 + 冪等）
  - README 加入「3 分鐘快速開始」區塊
- 中期（推薦）：
  - 提供 Windows GUI 安裝器（setup.exe）
  - 提供 macOS/Linux 一鍵腳本（brew bundle / apt）
- 長期（願景）：
  - 可攜式 Pi Harness：解壓即用，不需系統安裝

---

## Round 4：信任與透明度

### 安全工程師
核心問題：
> 用戶為什麼要信任「跑這個腳本」？

MECE 信任要素：

| 要素 | 說明 |
|------|------|
| 透明 | 清楚列出會做什麼 |
| 可驗證 | 用戶可檢查腳本內容 |
| 最小權限 | 只在必要時要求管理員 |
| 可逆 | 提供 uninstall |
| 開源 | 程式碼公開、可審計 |

**具體建議：**

1. README 加入「信任檢查清單」區塊：
   - 列出：
     - 會安裝什麼
     - 會修改哪些檔案
     - 不會做什麼
   - 附上：
     - MIT 授權
     - 程式碼連結
     - 隱私聲明

2. 腳本開頭：
   - 簡短說明 + 連結至 README
   - 要求確認（y/N）

3. 提供 uninstall 腳本：
   - scripts/uninstall.py
   - 移除 Pi 配置（可選）
   - 還原備份

### UX 設計師
P0 用戶的信任設計：

- 使用友善圖示：
  - ✅ 安全的操作
  - ⚠️ 需要你確認的操作
  - ❌ 失敗的操作

- 避免：
  - 大段技術文字
  - 要求「相信我，跑就對了」

### 可及性倡議者
- 使用簡單語言，避免黑話
- 提供中英雙語提示（或至少英文）
- 確保色盲可讀（不使用純顏色區分）

### PM（收文）
信任設計：

- README 加入「為什麼你可以信任這個專案」區塊
- 腳本加入「信任聲明」
- 提供 uninstall 腳本
- 所有程式碼開源、可審計

---

## Round 5：LLM 配置體驗

### 跨平台工程師
問題：
- 目前：掃描 Ollama / LMStudio，要求用戶手動輸入編號
- 痛點：
  - 若用戶沒跑 LLM 服務 → 不知道要怎麼做
  - 若用戶有跑 → 但不知道選哪個

**建議：**

1. 若偵測到 LLM：
   - 顯示推薦選項（根據效能/大小）
   - 標註「推薦」

2. 若未偵測到 LLM：
   - 提供友善提示：
     - 「若要使用本地 LLM，可安裝 Ollama：
       - Windows: winget install Ollama.Ollama
       - macOS: brew install ollama
       - 安裝後重新執行此腳本」
   - 或提供 API Key 模式（OpenAI / Anthropic / 其他）

3. 提供「稍後設定」選項：
   - 不強迫現在選

### UX 設計師
LLM 配置應：
- 不阻斷主流程
- 提供「先用雲端 API，後換本地」的選項
- 清楚說明「這會影響 AI 回答品質」

### PM（收文）
LLM 配置策略：

- 不阻斷：LLM 配置失敗不影響 Pi 安裝
- 提供預設推薦
- 支援：
  - 本地 LLM（Ollama / LMStudio）
  - 雲端 API（OpenAI / Anthropic / 其他）
  - 稍後設定

---

## Round 6：可逆性與 Cleanup

### DevOps/SRE
MECE 可逆性：

- 安裝前：
  - 備份 ~/.pi/agent 到 ~/.pi/agent.backup.{timestamp}
- 安裝後：
  - 提供 uninstall 腳本
  - 提供 restore-from-backup 指令

### 安全工程師
- uninstall 不應：
  - 刪除用戶自己的專案
  - 刪除 Pi 核心（除非用戶明確要求）
- 應：
  - 移除 skills / rules / extensions
  - 還原 settings.json（若備份存在）

### PM（收文）
Cleanup 策略：

- 提供 scripts/uninstall.py：
  - 移除 Pi 配置
  - 可選：卸載 Pi
  - 可選：還原備份
- README 說明 cleanup 步驟

---

## Round 7：README 與文件重構

### UX 設計師
README 問題：
- 資訊太多，P0 用戶會暈
- 需要「快速開始」區塊在最上方

**建議 README 結構：**

1. 標題 + 一句話說明
2. 🚀 3 分鐘快速開始（最上方，最醒目）
   - 一個指令
   - 一個截圖（可選）
3. ✅ 信任檢查清單
4. 📖 更多說明（摺疊）

### CLI 前端設計師
快速開始區塊（範例）：

```
🚀 3 分鐘快速開始

如果你從未使用過 Pi，只需：

  1. 安裝 Git（若尚未安裝）
  2. 執行：

     git clone https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness.git
     cd CKs_PI_Code_Agent_Harness

  3. 執行：
     - Windows: .\install.bat
     - macOS / Linux: bash install.sh

  4. 依照畫面提示操作即可
  5. 完成後，執行: pi

  就這樣！
```

### PM（收文）
README 重構：

- 最上方：3 分鐘快速開始
- 中段：信任檢查清單
- 下方：更多說明（摺疊）
- 確保 P0 用戶只看前 30 行就能開始

---

## Round 8：CI / 自動化 / 進階場景

### 進階用戶代言人
需求：
- 非互動模式（--auto）
- CI 集成
- 自訂 skills / rules
- 不要求 TTY

**建議：**
- 支援 --auto 旗標：
  - 使用預設值
  - 不要求確認
- 環境變數支援：
  - PI_MODEL=xxx
  - PI_API_KEY=xxx
- Dockerfile 範例

### DevOps/SRE
CI 場景：
- 在 GitHub Actions / GitLab CI 中使用
- 需冪等
- 需非互動

**建議：**
- 提供 .github/workflows/example.yml
- 提供 Dockerfile 範例

### PM（收文）
進階場景：

- 支援 --auto 模式
- 提供 CI 範例
- 提供 Dockerfile 範例

---

## Round 9：跨平台細節

### 跨平台工程師
MECE 拆解：

**Windows:**
- 問題：
  - 管理員權限
  - 路徑分隔符號
  - Git Bash 依賴
- 建議：
  - install.bat 改進：
    - 更友善的權限提示
    - 更明確的錯誤訊息
  - 中期：setup.exe（NSIS / Inno Setup）

**macOS:**
- 問題：
  - Homebrew 依賴
  - SIP / 權限
- 建議：
  - 使用 brew bundle（Brewfile）
  - 提供更明確的 Homebrew 指引

**Linux:**
- 問題：
  - 套件管理器多樣
  - 權限問題
- 建議：
  - 自動偵測套件管理器（apt / dnf / pacman）
  - 提供 sudo 提示

### PM（收文）
跨平台策略：

- 短期：改善現有腳本
- 中期：平台專屬安裝器
- 長期：可攜式版本

---

## Round 10：最終收文與行動清單

### PM（總結）
綜合所有討論，以下是 MECE 行動清單：

### 🔴 高優先（立即可做）

1. **README 重構**
   - 最上方加入「3 分鐘快速開始」
   - 加入「信任檢查清單」
   - 摺疊高級內容

2. **install.bat / install.sh 改進**
   - 加入信任聲明
   - 加入進度提示（[1/6]...）
   - 冪等處理
   - 更友善的錯誤訊息

3. **setup.py 改進**
   - 加入 --auto 模式
   - 加入「稍後設定 LLM」選項
   - 加入 LLM 推薦提示

4. **新增 uninstall.py**
   - 移除配置
   - 可選：卸載 Pi
   - 可選：還原備份

### 🟡 中優先（短期）

5. **Windows GUI 安裝器（setup.exe）**
   - 使用 NSIS / Inno Setup
   - 圖形化進度條
   - 內建依賴檢查

6. **macOS/Linux 一鍵腳本**
   - brew bundle（macOS）
   - apt / dnf / pacman 自動偵測（Linux）

7. **CI / Docker 範例**
   - .github/workflows/example.yml
   - Dockerfile

### 🟢 低優先（長期）

8. **可攜式 Pi Harness**
   - 內建 Node + Python
   - 解壓即用
   - 不污染系統

9. **Web-based 安裝嚮導**
   - 瀏覽器版安裝嚮導
   - 逐步圖文說明

---

## 附錄：用戶旅程（P0 目標流程）

```
[用戶] 看到 GitHub README
  ↓
[用戶] 看到「3 分鐘快速開始」
  ↓
[用戶] git clone + cd
  ↓
[用戶] .\install.bat（或 bash install.sh）
  ↓
[腳本] 顯示信任聲明 + 功能說明
  ↓
[用戶] 輸入 y
  ↓
[腳本] [1/6] 檢查環境...
[腳本] [2/6] 安裝 Node.js（若需要）
[腳本] [3/6] 安裝 Pi...
[腳本] [4/6] 掃描 LLM...
[腳本] [5/6] 套用配置...
[腳本] [6/6] 完成！
  ↓
[腳本] 顯示成功畫面 + 下一步
  ↓
[用戶] 執行 pi
  ↓
[用戶] 開始使用 Pi + Skills ✅
```

---

## 附錄：信任檢查清單（範例）

```
✅ 信任檢查清單

本專案：
  - 開源（MIT 授權），程式碼可審計
  - 不收集使用資料
  - 不呼叫外部追蹤 API
  - 不修改系統環境變數
  - 不偷偷安裝不明軟體

本腳本會：
  - 檢查 Git / Python / Node.js
  - 安裝 Pi（AI 助手核心）
  - 套用開發 Skills 與規則
  - 掃描本地 LLM 服務

來源：
  - GitHub: https://github.com/Chiakai-Chang/CKs_PI_Code_Agent_Harness
  - 授權: MIT
```
