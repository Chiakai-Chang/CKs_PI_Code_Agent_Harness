# 復盤：「沒發生」不等於「做不到」——同一天犯三次的同一個錯（2026-08-03）

這份文件記錄的不是三個技術發現，是**同一個推理瑕疵連續出現三次**。

三次都不是知識不足。三次都是：**觀察到某件事沒發生，就推論它做不到，而沒有先去排除「是不是我沒把它打開」或「是不是有別的東西在干擾」。**

三次裡有兩次被使用者當場質疑才翻案。若沒被質疑，三個錯誤結論都會被寫進文件當成事實。

---

## 一、三個實例

### 實例 1：孤兒進程造成的假 OOM

跨專案效能測試中，背景任務回報「完成」後，`llama-bench.exe` 並未真正退出，仍握著 **82.52 GiB** 顯存。

下一次測試的失敗訊息是：

```
ggml_vulkan: Device memory allocation of size 704643072 failed.
ggml_vulkan: vk::Device::allocateMemory: ErrorOutOfDeviceMemory
```

這句話**讀起來像「這個設定不受支援」**，實際上是「顯存被自己的殘留進程佔走了」。

差一步就把「Vulkan 拒絕量化 KV 快取」寫成結論。清掉孤兒進程後重測，該設定完全正常。

### 實例 2：沒讀啟動時的能力探測行

做了一整輪 backend 效能比較，得到一組乾淨、可重現、誤差棒漂亮的數字，並據此下了結論。

但從頭到尾沒有去讀啟動日誌裡的能力探測輸出：

```
resolve_fused_ops: Lightning Indexer not supported, set to disabled
resolve_fused_ops: fused ... HC pre / comb / post not supported, set to disabled
```

其中一個 backend 的四個融合 kernel 全部停用、另一個全部啟用。**兩邊跑的根本不是同一條程式路徑。**

數字本身沒有錯。錯的是「我以為我在比什麼」。在不知道這件事的情況下，任何「為什麼 A 比 B 快」的解釋都是編的。

### 實例 3：沒讀 API 完整簽章就宣告功能不存在

驗證「背景工作完成後能否從脫離的 timer 喚醒閒置的 agent」。

實測結果：訊息確實進了 transcript（`message_start` / `message_end`），但**沒有任何 assistant 回合**。當下的判定是「`pi.sendMessage()` 只能排隊，不能觸發回合」。

真相是漏了第二個參數：

```typescript
pi.sendMessage(msg, { triggerTurn: true, deliverAs: "followUp" });
```

`triggerTurn: true` 的官方說明就是 *"If agent is idle, trigger an LLM response immediately."*，寫在 `@earendil-works/pi-coding-agent` 的 `docs/extensions.md`。

補上參數後一次通過：`agent_start → turn_start → [custom message] → assistant 回應 → turn_end → agent_end → agent_settled`。

**更難堪的是**：本 repo 既有的 `pi-extensions/compact-continuation-bridge/index.ts` 一直都寫對，早就帶著 `{ deliverAs: "followUp", triggerTurn: true }`。答案就在自己的程式碼裡。

### 變體：環境沒撐到事件發生

同一個 spike 的第一次執行，timer 完全沒觸發。

原因不是功能不存在，而是 `--mode rpc` 讀到 stdin 的 EOF 就直接結束了——process 在 timer 到期前就死了。把 stdin 撐住後立刻正常。

同一類瑕疵的第四次現身：**把「測試環境沒活到那個時間點」誤讀成「那件事不會發生」。**

---

## 二、共同結構

| 步驟 | 三次都一樣 |
|---|---|
| 觀察 | 預期的事情沒有發生 |
| 跳躍 | 推論成「這件事做不到／不支援」 |
| 缺漏 | 沒有把「缺席」本身當成一個待解釋的現象 |
| 代價 | 錯誤結論差點被寫進永久文件 |

「缺席」是所有觀察裡最弱的一種證據。它同時相容於「功能不存在」「我沒開對」「有東西擋住」「還沒輪到它」四種解釋，而我每次都直接選了最沒建設性的那個。

---

## 三、可執行的檢查

任何「X 沒發生／不支援／做不到」的結論，在寫下來之前必須先排除這三件事：

1. **開關**——該 API／旗標的**完整簽章**讀過了嗎？有沒有第二個參數、選項物件、環境變數？先讀文件，再下結論。
2. **干擾**——資源是不是被自己稍早留下的進程佔著？先查進程與資源用量，並跟乾淨基準值比對。
3. **存活**——測試環境活到事件應該發生的時間點了嗎？stdin、timeout、process 生命週期都算。

另外兩條同源的紀律：

4. **每次載入模型／後端都要讀啟動的能力探測行。** 旗標被接受不代表功能生效；更陰險的是功能不報錯、靜默降級到退路。
5. **比較兩個設定之前，先確認它們跑的是同一條路徑。** 否則數字再乾淨，解讀也是虛構的。

---

## 四、附帶確立的事實（供後續設計引用）

驗證過程本身產出了三個可用的結論：

- `pi.sendMessage(msg, { triggerTurn: true, deliverAs: "followUp" })` **可以**從脫離的 `setTimeout` callback 喚醒閒置的 agent。實測 timer 於 `+12.1s` 觸發、agent 自行醒來並正確回應。
- extension 的 event loop 在 agent 閒置期間**持續存活**，`setTimeout` 準時觸發。
- 事件序列包含 `agent_end` 與 `agent_settled`；後者是「全部做完、佇列已空」的確定訊號，適合作為「該停還是該通知人類」的判斷點。

這三點是「背景工作完成後自動續跑」設計的地基，且已用實測而非推測確立。
