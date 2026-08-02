# 復盤：Prefix-Stabilization 有標價，而我們自己的 bridge 正在付（2026-08-03）

`pi-rules/performance.md` 的「上下文內核協議」第 1 條寫得很清楚：

> **Prefix-Stabilization (KV-Cache 穩定化)**：始終將穩定的指令（System Prompt, Rules）放在
> Prompt 最前端。動態元數據（日期、Session ID）必須放在穩定前綴之後，**嚴禁插入前綴中間**。

規則沒問題。缺的是兩樣東西：**這條規則違反時的實際代價**，以及**我們自己有沒有在遵守**。

兩個答案都在下面，而且第二個不好看。

---

## 一、標價：前綴一變，要付多少

在 gfx1151（Radeon 8060S，128 GB 統一記憶體）上以 llama.cpp Vulkan 後端實測，
模型為 DeepSeek-V4-Flash-0731 的 2-bit 量化版（80.76 GiB）。

### 前綴穩定時，prompt cache 幾乎全中

| 情境 | 送進去的 context | 實際重算 | 快取命中 | 耗時 |
|---|---:|---:|---:|---:|
| 首次送出 3,010 token | 3,010 | 3,010 | 0 | — |
| 同一段再送一次 | 3,010 | **4** | 3,006 | — |
| 接續下一輪對話 | 3,025 | **15** | 3,006 | — |
| 12.6K 對話後接 `<tool_result>` | 12,656 | **531** | 12,125 | 7.1 秒 |
| 切走再切回原前綴 | 12,656 | **4** | 12,652 | 0.6 秒 |

純 append 只重算新增的部分。Agent 的正常工具迴圈完全吃得到快取。

### 前綴一變，全毀

| 情境 | 實際重算 | 耗時 |
|---|---:|---:|
| 12.6K 對話，**只在 system prompt 加了一行時間戳** | **12,674（全部）** | **225.8 秒** |

改動內容不到一行。代價是把整段對話從頭算一次，將近**四分鐘**。

### 為什麼在本地模型上特別致命

同一台機器的 prefill 吞吐量會隨 context 深度崩潰。六輪對話，每輪固定追加約 4.2K token，
**每輪重算的 token 數完全相同**：

| 輪次 | context 深度 | 重算 token | prefill 耗時 | 有效 prefill |
|---:|---:|---:|---:|---:|
| 1 | 4,219 | 4,219 | 42.9 秒 | 98 t/s |
| 3 | 12,641 | 4,215 | 106.9 秒 | 39 t/s |
| 6 | 25,279 | 4,215 | 173.1 秒 | **24 t/s** |

同樣的工作量，第六輪要花四倍時間。也就是說**前綴失效的代價本身會隨對話變長而放大**——
在深處打破快取比在淺處貴得多，而 agent 工作正是越做越深。

---

## 二、稽核：我們自己有在遵守嗎

沒有。

`pi-extensions/planning-with-files-bridge/index.ts:202`，註解自己寫著
「Before each agent turn: inject plan context into system prompt」：

```typescript
pi.on("before_agent_start", (event, ctx) => {
  const planContext = injectPlanContext(ctx.cwd, maxChars, isSlim);
  if (!planContext) return;
  return {
    systemPrompt: (event.systemPrompt ?? "") + "\n\n" + planContext,
  };
});
```

`planContext` 的來源是 `task_plan.md` 與進度紀錄——**內容本來就會隨工作推進而變**，
卻被接進 system prompt，也就是 context 的最前端。

更糟的是同一個 bridge 的 `tool_result` handler 會主動促成這件事：

```typescript
const msg = "[planning-with-files] Update progress.md with what you just did. ...";
```

於是形成一個設計上的迴圈：

> 模型寫檔 → bridge 提醒更新進度 → 進度檔變了 → 下一輪 system prompt 跟著變 →
> **整段 context 重算** → 越到後面越貴

這不是「寫錯了」——注入計畫脈絡是刻意且有用的設計。錯的是**放置位置**，
而規則第 1 條講的正是位置。

---

## 三、修法：同樣的資訊，換一個投遞通道

`before_agent_start` 除了 `systemPrompt` 之外還有第二個回傳欄位
（見 `@earendil-works/pi-coding-agent` 的 `docs/extensions.md`）：

```typescript
return {
  // 持久訊息，存進 session、送給 LLM，但接在 context 尾端
  message: { customType: "my-extension", content: "...", display: true },
  // 取代本輪 system prompt，位於前綴
  systemPrompt: event.systemPrompt + "\n\n...",
};
```

把易變的 `planContext` 從 `systemPrompt` 換成 `message`，**送給 LLM 的資訊完全相同**，
但位置從前綴移到尾端，前綴因此保持穩定，快取得以延續。

這同時也更符合 `performance.md` 第 2 條的 U 型配置——計畫狀態屬於「當前意圖」，
本來就該靠近 context 末端，而不是混在最前面的穩定指令區。

### 要一併處理的取捨

`message` 是**持久**的：每輪注入就在 transcript 裡多一份副本，context 會累積。

- 只換通道：快取保住了，但 50 輪就多出 50 份計畫快照
- 加上變更偵測：注入前比對內容雜湊，**沒變就不注入**

兩者要一起做。沒變的輪次完全零成本，有變的輪次只付一份訊息的長度——
相較於一次 225.8 秒的全量重算，這個交換在任何模型上都划算，在本地模型上是數量級的差距。

`slim` profile 下 `planningBridgeMaxChars` 預設 600，單份副本約 150 token，
累積速度遠低於重算成本。

---

## 四、尚未執行

本文件只做記錄與稽核，**沒有修改 `planning-with-files-bridge`**。

理由是 `pi-rules/AGENTS.md` §4 的 GEPA 紀律：對既有行為的永久性修改應走獨立分支、
沙箱試跑，再以 diff 交付審查，而不是直接套用。修改注入通道會影響模型的計畫感知，
屬於需要實測驗證的改動，不該在一次文件整理裡順手改掉。

建議的下一步：開 `evolve/planning-bridge-prefix-stability` 分支，
實作「改用 `message` + 內容雜湊變更偵測」，並以同一份多輪對話量測前後的重算 token 數。

---

## 五、可直接引用的結論

1. **Prefix-Stabilization 的代價是可量測的**，不是抽象原則。本硬體上一次前綴失效 = 全量重算，
   12.6K 對話約 225.8 秒。
2. **代價隨深度放大**：同樣的重算量在 25K 深度要花 4K 深度的四倍時間。
3. **易變內容一律走 `message`，不進 `systemPrompt`。**
4. **注入前先比對是否真的變了**；沒變就不要送。
5. 上述四點與模型無關，但在本地模型上從「浪費」升級為「不可用」。
