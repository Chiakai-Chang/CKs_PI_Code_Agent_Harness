# 校準層:哪些數字搬出程式碼,哪些留下(T-A2)

**日期:2026-08-11**
**規則來源:** `CLAUDE.md`「三層,而一個改動只屬於其中一層」——
protocol(C.A.S.E.,不得提及任何模型)/ enforcement(bridge,依賴 Pi 的事件模型)/
calibration(門檻、預算,依賴特定模型)。
**外部依據:** Harness-Bench(arXiv 2605.27922,5,194 條軌跡)——
能力是 **model–harness 配對**的屬性,不是模型的屬性。

## 為什麼這是個問題

換模型時,一個校準錯的常數**不會報錯**。它只會讓閘太早放手、讓提醒永遠不來,
而所有測試照樣全綠。這是「安靜的不合適」,比壞掉更難發現。

## 搬出去的(四個)

| key | 值 | 校準自 | 消費者 |
|---|---|---|---|
| `caseClaimRefusalTurns` | 8 | 2026-08-09 量測(**回合**不是呼叫 —— 這個模型一回合發五個平行呼叫) | `phase-gate.ts::refusalTurns` |
| `goalRestateThreshold` | 12 | 2026-08-09(該模型 32.4% 的呼叫在第 12 次之後) | `GoalRestate` 建構參數 |
| `goalRestateMax` | 2 | 同上 | 同上 |
| `queueListingCap` | 5 | 未量測 —— 一次能讀多少是模型屬性,標示為校準以便日後量 | `phase-gate.ts::claimThird` |

程式碼裡的常數**留著當最後防線**:config 讀不到就用它。
`0`、`"12"`、`true`、`2.5`、負數都會被拒絕並落回常數 —— 尤其 `0`,
它會讓提醒在每一次工具結果後都出現。

### 反轉了一條有文件的決定

`refusalTurns` 原本寫著「刻意不讀全域:這個設定只作為專案層級的調緊」。
那個理由講的是**專案檔案**的信任邊界,而那條邊界沒有改變(專案仍只能在 8–12 內調緊)。
全域檔是我們自己的。把數字留在程式碼裡,等於讓「對一個模型、在一天內量到的 8」
變成執行碼裡的常數 —— 正是 T-A2 要消除的東西。原文已引在程式碼註解裡,沒有刪掉。

## 沒有搬、也不打算搬的(寫下來,否則下次會被重建)

* `MAX_FIELD_CHARS` (256)、`MAX_APPROVAL_CHARS` (40)、`JSON_SCAN_BUDGET` (200k)、
  `AUTO_EXEC_CHAR_BUDGET` / `MAX_ENTRIES` —— **結構性上限**,防的是失控的輸入,
  不隨模型改變。
* `MAX_INJECT_CHARS`、`caseBridgeMaxChars`、`planningBridgeMaxChars` ——
  注入預算,**後兩個已經在 config 裡**;第一個是同族,若要動就整族一起動。
* `REPEAT_CALL_LIMIT` (4)、`REPEAT_OFFENCE_LIMIT` (3)、`MAX_INTENT_NUDGES` (2) ——
  **看起來像校準,而且可能真的是**。沒有一起搬,是因為 T-A2 的清單是帳本點名的三個,
  而一次搬七個會讓「哪一個改動造成什麼」再也說不清。
  **觸發條件:換模型後若出現迴圈守衛過早或過晚介入,先搬這三個。**
* `PROACTIVE_COMPACT_PERCENT` (80) —— 屬於 context 校準,已有
  `scripts/calibrate-context.py` 這條獨立的機器層路徑,不要開第二條。

## 一致性(新裝 / 更新 / 重裝都一樣)

值寫在 `pi-config/harness-config.json`(進版控),機器層覆蓋走
`harness-config.local.json`(gitignored),兩者由 `scripts/restore.py` 合併 ——
**沿用既有機制,沒有新增第二套**。`tests/test_governance.py` 要求每個 key 都有消費者,
`tests/test_calibration_layer.py` 要求 config 的值與程式碼的 fallback 一致,
所以兩邊漂移會紅。

## 測試怎麼寫的(以及為什麼要這樣寫)

出貨值與 fallback 是同一個數字,所以**只驗出貨情境的測試分不出「讀了 config」與
「根本沒讀」**。每一條都對著 fixture root 跑。

第一版仍然漏了一個:它驗 `listingCap()` 這個輔助函式,而把呼叫點改回
`slice(0, 5)` 之後**十條全綠**。加了 `useHarnessRoot()` 接縫、改從 `check()` 的
拒絕文字驗之後,同樣的破壞會紅。**與同一天早上那個死掉的守衛是同一種缺陷。**
