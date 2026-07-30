# 復盤：放棄 Laguna，以及 Strix Halo 上的外部證據整理（2026-07-30）

接續 [2026-07-29 交接](2026-07-29-handoff.md)。這一輪換了模型、撞了三個新坑、修了三個儀器缺陷，
並且從五份社群 model card 蒐集到一批**可直接搬用**的外部量測。

結論先講：**Laguna-S-2.1 放棄，改測 Qwythos-27B-v1（`qwen35`）。**
原始問題（約 9% 的回合拒絕或捏造）**仍然沒有診斷**，這一輪也沒有解決它。

---

## 一、Laguna 這一輪實測到什麼

> **這份文件裡的所有數字都來自單一台開發機**，不是這個 repo 的預設值，也不保證在別的機器上成立。
> 硬體類別（AMD Strix Halo 級的 APU，統一記憶體，裝置回報約 110 GiB 可用）之所以寫出來，
> 是因為離開它那些數字就沒有意義，不是因為它是建議配備。
>
> **模型啟動腳本與 `pi-config/models.json`、`pi-config/settings.json` 都是機器本機檔**
> （後兩者在 `.gitignore` 裡，只有 `.example` 進版控）。這個 repo **不預設任何模型**，
> 也不應該被改成預設任何模型 —— 換模型是每台機器自己的事。
> 下面提到啟動腳本時一律指「本機的模型目錄」，路徑刻意不寫。

檔案：`Laguna-S-2.1-Uncensored-APEX-I-Balanced.gguf`，85,229,205,664 bytes = **79.4 GiB**
（HF 頁面寫 85.2 GB 是十進位，換算時差 6 GB，足以誤判裝不裝得下）。

### 1. 只有官方 build 認得 laguna

掃各 build DLL 內的 arch 字串（**字串檢查，不是載入測試**）：

```
llama-bin-win-hip-radeon-x64  (b10173)   laguna: 有
llama-bin-win-vulkan-x64      (b10173)   laguna: 有
llama-bin-win-rocm7-gfx1151   (lemonade)  laguna: 無
```

lemonade 是這台機器的 PP 冠軍。換 Laguna 等於**同時換引擎**，
[換模型驗收清單](2026-07-29-model-swap-checklist.md) §5 明講這是兩個變數一起動。
這一點本身就讓「Laguna vs Fable」不可能是乾淨的模型比較。

### 2. 262144 ctx 可行，1M 不可行

`-c 262144` 實際載入成功並服務請求，以下數字**逐行取自 server log**，不是計算：

```
load_tensors:  ROCm0 model buffer size = 80689.35 MiB
load_tensors:  CPU_Mapped model buffer =   588.00 MiB
llama_kv_cache: 12288.00 MiB (262144 cells, 12 layers)   <- global 層
llama_kv_cache:   144.00 MiB (  1024 cells, 36 layers)   <- SWA 層
sched_reserve:  ROCm0 compute buffer   =   144.00 MiB
```

**SWA 裁切有效**：48 層中 36 層是 sliding window(512)，不論 `-c` 多大都只配 1024 cells。
只有 12 個 global 層隨 context 成長，換算 **48 KiB/token**。
ROCm0 合計 93,265 MiB，剩約 17,000 MiB。

由這個實測值**外推**（非觀察值）：

```
-c 393216   KV 18,432 MiB   總 ~99,400 MiB
-c 524288   KV 24,576 MiB   總 ~105,500 MiB   很緊
-c 1048576  KV 49,152 MiB   總 ~130,100 MiB   放不下
```

模型卡宣傳的 1M 在這台做不到。

### 3. 一組旗標讓載入直接 crash（未隔離）

```
ROCm error: unspecified launch failure
current device: -1, in function ggml_cuda_kernel_launch
```

crash 的那次帶了 `--no-mmap` `-fa on` `-b 4096` `-ub 2048` `--no-context-shift`；
成功那次沒有，log 顯示 `flash_attn = auto`。**四個旗標是一起移除的，沒有逐一隔離。**

外部證據支持「FA 是嫌疑最大的那一個」：
`jcbtc/Laguna-S-2.1-Chadrock-ROCmFP4-StrixKVSpine-V4` 的 Runtime V2 patch notes 寫

> The first runtime release could lose the Vulkan device during a very deep Flash Attention prefill on RADV/Strix Halo

他們整個 V2 runtime 就是在修 laguna + Flash Attention 在 Strix Halo 上的 device-lost，
做法是把大的 FA X grid 拆成較短的 Vulkan dispatch。**這是獨立第三方在同型硬體上的觀察**，
但那是 Vulkan/RADV 路徑，我們是 HIP，不能直接等同。

### 4. 部分回合進入 token 重複迴圈，燒到 max_tokens

server log：

```
slot process_toke: task 6782 | n_decoded = 1096, n_remaining = 31675, next token: 14 ''
slot print_timing: task 6782 | n_decoded = 1094, tg = 21.99 t/s
```

token 14 detokenize 是 `〈|`，id 2 是 `〈|EOS|〉`、id 24 是 `</assistant>`。
以 22 t/s 計，`max_tokens: 32768` 的一個失敗回合要 **25 分鐘** —— 一批量測根本跑不完。

載入時每次都印：

```
W load: special_eos_id is not in special_eog_ids - the tokenizer config may be incorrect
W load: special_eot_id is not in special_eog_ids - the tokenizer config may be incorrect
```

**但不要把這當成診斷。** 同一批裡有回合正常結束（`finish_reason=stop`、`out_tok=15`），
所以 EOG 不是全壞。我一度寫成「模型不會停」，那句話過頭了，已更正。
另一個同樣合理的解釋是取樣太緊（見第三節第 3 點）。

### 5. request 層 prompt cache 不是變因

ABAB 對照（輕負載 fixture 660 tok、13 tools、`--max-tokens 2048`，
on/off/on/off 交錯以排除時間次序）：

```
round 1  A cache ON   0/6   truncated=6
round 1  B cache OFF  0/6   truncated=6
round 2  A cache ON   0/6   truncated=6
round 2  B cache OFF  0/6   truncated=6
```

`cache_prompt` 開關**毫無差別**，先前登錄的 H1 被否定。

但同一份 fixture 在半小時前是 **4/12 clean + 8 次回聲停止**，現在是 24/24 全部撞上限。
差別只有「累積跑了幾十個請求」。這符合先前登錄的 H2（狀態隨請求累積漂移），
而 `cache_prompt:false` **關不掉 server 層那個 `prompt cache is enabled, size limit: 8192 MiB`**。
`--cache-ram 0` 的對照**沒跑成**（背景任務被中止），所以 H2 仍未驗。

這條線索直接對上 2026-07-29 交接檔裡「最大未解釋變異」（同配置 0/12 ↔ 6/8、
剛啟動 vs 跑兩小時）。**「暖機」可能是錯的框架，真正的變數可能是請求累積後的快取／slot 狀態。**

### 6. 決定放棄的量化理由

`jcbtc` 那份 Chadrock V4（專為 Strix Halo 調校、tool-eval 上贏官方 29%）自報：

| Tool-Eval disputed-19 | 接受的呼叫 |
|---|---|
| Chadrock ROCmFP4 V4 | 80/114 = **70.18%** |
| Poolside 官方 Q4_K_M | 62/114 = **54.39%** |

**連最佳社群調校版的工具呼叫接受率也只有 70%，官方只有 54%。**
我們量到 APEX I-Balanced 4/12（33%）與這個家族一致。
Laguna 對一個以工具呼叫為核心的 harness 就是不夠可靠 —— 這不是配置問題。

---

## 二、這一輪修掉的儀器缺陷（三個都在工作區，未 commit）

### 1. fixture 不可重建 —— `scripts/make-probe-fixture.py`（新增，20 tests）

2026-07-29 讓一整天比較作廢的第一號錯誤是 fixture 大小沒對齊真實負載，
而且那些 fixture 是臨時在 `/tmp` 拼出來的、**事後無法重建**，所以連「用同一份檔案重測」都做不到。

新腳本從**釘死的 commit** 產生 fixture、記錄 sha256 與 manifest（manifest 存的是解析後的
40 字元 SHA，不是 `HEAD` —— 記成 `HEAD` 的 manifest 下一個 commit 就重建不出來）。

一個之前沒意識到的前提寫進了腳本文件：**fixture 由 bytes 釘死，token 數是
「(fixture, 模型) 配對」的性質**。Qwen 與 Laguna 的 tokenizer 不同，
「15,287 tokens」在兩邊不是同一個檔案。跨模型比較要比 sha256，不是比 token 數。

實際產生的兩份（Laguna tokenizer 計數）：

```
fixture-660tok.txt     1,811 bytes   660 tokens   cc0514d57575
fixture-15280tok.txt  43,551 bytes 15,280 tokens   950938aa539a
commit f56af498496e
```

### 2. 逾時被記成 error —— `scripts/probe-tool-calls.mjs`

2026-07-29 已經在 `probe-retry-recovery.mjs` 修過這個（逾時計為 fail），
**但同一個教訓沒有搬到隔壁腳本**，於是 15,280 fixture 的第一個請求就撞上：

```
run 1: REQUEST FAILED fetch failed
```

而 server 那邊還在跑（`n_tokens = 18575`）。undici 的 300 秒 headers timeout 到了，
client 放棄，腳本記成 error —— **最容易失敗的案例被系統性地移出分母，回報的成功率偏高。**

已修：`PROBE_TIMEOUT_MS`（預設 240000）+ `AbortSignal.timeout`，逾時歸類為 `shape=timeout` 且算 fail；
只有連線被拒、載入中 503、JSON 壞掉這種**儀器壞掉**才留在 error。

### 3. 失控回合無法設上限 —— 新增 `--max-tokens` 與 `truncated` 形狀

`max_tokens` 原本寫死 32768。EOG 有問題的模型每個沒呼叫工具的回合都會跑到上限，
25 分鐘一次，一批量不完。新增 `--max-tokens`（預設仍是 32768，**維持舊基線可比**），
並把 `finish_reason=length` 且零呼叫獨立成 `truncated` —— 「不肯動」與
「一直生到被切斷」是不同的病，不該併進 `no-call`。

### 4. 順手補的：parser 對 Laguna 格式靜默回傳 null

`pi-extensions/yes-hooks-bridge/index.ts` 新增分支 1c：

```
<tool_call>NAME<arg_key>key</arg_key><arg_value>value</arg_value></tool_call>
```

工具名是 wrapper 後的裸文字，沒有 `<function=>` 包裝，所以分支 1b 看不到、
分支 1 因為 body 不是 JSON 而放棄 → **回傳 null → 無 strike、無糾正、靜默卡死**。

這是**同一個洞的第三次**：先是 ```json 陣列，再是 Qwen 的 `<function=>`，現在是 Laguna。
形狀每次不同，機制每次一樣：template 教一種格式、parser 沒有對應分支、退化的回合把它當文字洩漏出來。
先寫 10 個測試確認全紅，才實作。即使放棄 Laguna 也留著 —— 成本是 20 行，
而這個類別的洞已經證明會反覆出現。

全套：`python -m unittest discover -s tests` → **Ran 406 tests, OK**。

---

## 三、外部證據整理（五份 model card，全部 Strix Halo / Ryzen AI Max+ 395）

來源與適用性：

| 來源 | arch | 能不能用 | 為什麼 |
|---|---|---|---|
| `SC117/Laguna-S-2.1-Uncensored-APEX` | laguna | 測過，放棄 | 工具呼叫不可靠 |
| `jcbtc/Laguna…Chadrock-StrixKVSpine-V4` | laguna | **不能** | 要 Ciru ROCmFPX fork，且安裝路徑全是 Linux |
| `christopher-kapic/MiMo-V2.5-ROCmFP4` | mimo2 | **不能** | 要 ROCmFPX fork；且卡片自陳有我們正在治的病 |
| `jcbtc/chadrock3.6-27b-coder-rocmfp4-mtp` | **qwen35** | 不能（fork） | 但**同 arch**，配置最可搬 |
| `jcbtc/qwable-27b…ULTRAQUALITY-7.61BPW` | qwen35 | 不能（fork） | MTP 參數與 acceptance 數據 |
| `mfielding92/SmartCode-Fable-5-CoT…` | qwen35 | 可以（stock） | 但是 coding CoT distill，非 agentic/tool 訓練 |

### 直接排除 MiMo-V2.5 的那句話

> MiMo-V2.5 can enter runaway chain-of-thought — "extremely long CoT (sometimes for hundreds of
> thousands of tokens) with no progress or tool calls" (#23074), reproduced on **Q8_0**

「長篇 CoT、沒有進度、沒有工具呼叫」就是我們的 `no-call` / `fabricated-completion`，
而且在 Q8_0 上重現，不是量化造成。拿它治這個病是反向操作。

### 可搬用的量測（同為 `qwen35` 架構）

**MTP acceptance 對 recipe 極度敏感，必須量：**

```
qwable UltraQuality  n_max 6, p_min 0.0, p_split 0.20, draft KV f16  -> 437/439 = 99.5%
同硬體、被取代的舊 recipe                                            -> 217/1762 = 12.3%
```

99.5% 對 12.3%。**不要假設 MTP 在幫忙**，Fable 量到 0.71–1.00 屬堪用，Qwythos 未知。

**同 arch 的成本曲線（chadrock3.6-27b，no-cache 強制掃描，每點生成 512 tokens）：**

```
 4,131 tok  prompt 315.97 t/s   decode 21.25 t/s
 8,227      308.66              21.82
16,419      286.62              21.64
32,803      251.76              17.35
65,571      201.49              12.51
130,467     142.00               7.08
```

harness 真實每輪 15,287 tokens 落在第三列附近，那裡 decode 還沒開始掉。
到 130K 掉到 1/3。**又一個「不需要追 1M context」的具體理由。**

**工具用途的 profile 一致關掉 thinking：**

```
qwable UltraQuality:    --reasoning off --reasoning-format none --reasoning-budget 0
chadrock3.6 27B:        reasoning off
chadrock3.6 35B ToolEval: --no-think, reasoning off
```

**但這條不是普世規則。** `SmartCode-Fable-5` 的卡片說法相反：

> Keep the reasoning block enabled, since this model's entire value proposition lives in how
> efficiently it uses that block. […] aggressive thinking-budget forcing is generally unnecessary
> and may hurt output quality on the hard tail of problems.

差別在那個模型的基底 `ThinkingCap-Qwen3.6-27B` 專門壓縮思考長度
（自陳平均少約 50% thinking tokens、最佳情況超過 90%、準確度差異低於 1%）。
所以「關掉 thinking」是**針對思考會失控的模型的補償措施**，不是通則。

**`--ctx-checkpoints 0 --checkpoint-every-n-tokens -1`** 出現在 validated profile 裡。
這是**另一個 server 端狀態機制**，正是我們懷疑造成跨請求漂移的那一類。量測階段應該一併關掉。

**KV 量化：三方衝突，我們維持 f16。**

| 來源 | 說法 |
|---|---|
| 我們 `KNOWN_ISSUES.md` | 量化 KV 是參數失控的**已證**原因 |
| MiMo card（ROCm 實測） | f16 比量化在 32k 深度**快 13%**；但量化 KV 換到 3.4× 的 context 容量 |
| chadrock3.6 27B lane | 用 `-ctk q4_0 -ctv q4_0` 跑 262144 |

我們有自己的實證、而且 VRAM 不缺，**維持 f16**。

**`power_dpm_force_performance_level=high` 值 +14% decode —— 但 Windows 上用不到。**
那是 Linux sysfs 路徑（`/sys/class/drm/card*/device/`）。記下來是因為它說明
「DPM governor 在 MoE decode 上不會升頻」這個現象存在；如果哪天搬到 Linux，這是單一最高價值的主機設定。

**釘死 chat template 的 hash。** chadrock3.6 35B lane 用
`Froggeric Qwen fixed chat template, SHA256 27d22ab352efbb63cdcc379cc58924f16b2949931e6f185b959f8930efc9520b`。
我們的 `C:\models\chat_template.jinja` 沒有記 hash，而「template 被靜默換掉」已經咬過我們一次
（漏 `--chat-template-file` 時 llama.cpp 不報錯）。應該記下來。

---

## 四、一個新發現的儀器方法論問題（比上面任何一條都重要）

`probe-tool-calls.mjs` 的設計是**跨模型釘死所有取樣參數**，註解寫得很清楚，理由也對：
比較兩個模型不該同時比較兩份啟動腳本的取樣差異。

但五份 model card 的建議取樣**沒有兩份相同**：

| 模型 | temp | top_p | top_k | min_p | repeat | 其他 |
|---|---|---|---|---|---|---|
| Fable-Fusion-711（MTP 限制） | 0.6 | 0.95 | 20 | 0.0 | **1.0 強制** | — |
| Laguna APEX | 0.6–1.0 | 0.95 | 20 | — | 未指定 | — |
| Laguna Chadrock release sampler | **1.0** | **1.0** | 20 | 0.0 | 1.0 | seed 42 |
| MiMo-V2.5 | 1.0 | 0.95 | — | 0.0 | 1.05 | — |
| Qwythos-27B | 0.6 | 0.95 | 20 | — | **1.05** | — |
| SmartCode-Fable-5 | **0.9** | 0.95 | **60** | 0 | 1.0 | **presence 1.0** |

而 `SmartCode` 那份把話講得最直白：

> **This model was tuned around these exact settings. Do not skip this section.**
> Bad sampler settings are the #1 cause of "the distill is broken" reports.

**所以釘死取樣讓比較乾淨，卻可能把每個模型都推出它被調校的區間 ——
這本身就是一種製造「沒有差別」的方式，正是 2026-07-29 讓六個結論全部倒掉的那個錯誤家族。**

而且我們已經看到疑似證據：Laguna 那個 token 14 迴圈是在 temp 0.6 / top_p 0.95 下發生的，
比 Chadrock 的 release sampler（temp 1.0 / top_p 1.0）**緊**；
而他們記載 BigCodeBench 貪婪解碼時出現「seven length-capped repetition loops」，
換成 release sampler 之後**七個全部自然結束**。

**修正做法：每個模型跑兩組 —— 卡片指定的取樣，以及共同基準取樣 —— 兩組都回報。**
單一組都會說謊：只用共同取樣會低估被推出調校區間的模型；
只用卡片取樣則把取樣差異混進模型差異裡。

---

## 五、Qwythos-27B-v1 為什麼是下一個（以及要怎麼測）

`empero-ai/Qwythos-27B-v1`，arch `qwen3_5`（GGUF metadata 顯示 `qwen35`），
Qwen3.5-27B dense 基底 + SFT→DPO→ESFT。GGUF repo 有 12 個檔，選
**`Qwythos-27B-MTP-Q8_0.gguf`（29 GB）**：

1. **量化從變數清單移除。** 2026-07-29 被撤回的第一號「根因」就是「Q4_K_M 不堪用」
   （6/6 重現不出來）。110 GB 的機器沒必要留著那個懷疑。
2. **stock llama.cpp 就能跑，而且 lemonade gfx1151 認得 `qwen35`**
   （掃 DLL：三個 build 都有 `qwen35` 與 `qwen3next`）。
   **引擎變數可以固定住 → 這是唯一能對 Fable 基線做單一變數比較的候選。**
3. **tool-call 格式 parser 已經支援**：
   `<tool_call><function=NAME><parameter=PARAM>value</parameter></function></tool_call>`
   就是分支 1b 的目標。harness 不必改。
4. 卡片指定 `repetition_penalty=1.05`，理由是
   「prevents rare non-terminating reasoning loops on long generations」——
   正好是 Laguna 今天燒掉 25 分鐘的病。

**廠商宣稱、未經驗證**：held-out terminal/tool-session perplexity 356.6 → 2.76、
在 emulated Claude-Code session 裡吃 `nmap` 輸出並發出正確的下一個 shell tool call。
這是我看過最貼近我們失效形狀的宣稱，但它是自述。

### bat 的預定內容（等檔案下載完）

lemonade gfx1151 build、`--jinja` 用 Qwythos 自帶 template（**不要**套 froggeric v21.3）、
`-c 262144`、f16 KV、`-t 6 -tb 6`（我們自己 llama-bench 量的，他們的 `-t 16 -tb 32` 沒調過）、
`--ctx-checkpoints 0`、`--cache-ram 0`、MTP 開但**要量 acceptance**。

### 驗收順序（不要跳）

1. `/props` 三件事：`model_path`、`chat_template` 第一行、log 裡的 `KV self size`
2. 等 `/v1/chat/completions` 回 200 才開始（載入中 `/props` 就會回應但那支回 503）
3. 探測跑兩組取樣（卡片 `--rep-pen 1.05` + 共同基準），乾淨區與 15k 目標值各一次
4. 只有探測明顯贏了，才動 harness 設定與真實 Pi session

---

## 六、仍未回答的問題

1. **原始問題沒有診斷。** 約 9% 的回合拒絕或捏造，在 671 到 26,052 tokens 之間量不出差別。
   換模型是在賭，不是在修。
2. **H2（server 層狀態漂移）未驗。** `--cache-ram 0` 的對照沒跑成。
   這是目前最可能解釋「同配置 0/12 ↔ 6/8」的假設，值得優先驗，而且與模型無關。
3. **262144 crash 的真正旗標未隔離。** 四個一起移除的。外部證據指向 `-fa on`，但那是 Vulkan/RADV 路徑。
4. **兩個新守衛（Guard 5 repeat-call、Guard 6 fabricated-work）仍然從未在真實 Pi session 裡跑過。**
   這是 2026-07-29 交接檔 §5.2 就列出的項目，這一輪也沒做。它只有單元測試。
5. `probe-retry-recovery.mjs` 逾時修完之後**還沒重跑**。

---

---

## 七、Qwythos-27B-v1 MTP Q8_0 實測（2026-07-30 當天完成）

本機啟動腳本（在模型目錄，不在版控內），lemonade gfx1151 build，`-c 262144`，f16 KV，
`-t 6 -tb 6`，MTP 開，`--cache-ram 0 --ctx-checkpoints 0`。

### 驗收

```
sha256sum -c SHA256SUMS --ignore-missing  ->  Qwythos-27B-MTP-Q8_0.gguf: OK
                                              34338ce4df38a49624b66f9d682f25bb1c460c83051b02d08797c6e6ea178025
載入時間             28.9 秒（Laguna 要 1 分 24 秒）
/props model_path    C:\models\Qwythos-27B-MTP-Q8_0.gguf
chat_template        Qwythos 自帶，161 行，無 froggeric，含 tool_call
n_ctx                262144
/v1/chat/completions 200
reasoning_format     deepseek 有效，reasoning_content 正常分離
```

### 記憶體（逐行取自 server log，非計算）

```
load_tensors:  ROCm0 model buffer size = 26402.70 MiB
load_tensors:  ROCm_Host model buffer  =  1288.28 MiB
llama_kv_cache: size = 16384.00 MiB (262144 cells, 16 layers)   <- target，full-attention 層
llama_kv_cache: size =  1024.00 MiB (262144 cells,  1 layers)   <- MTP draft
llama_memory_recurrent: size = 1047.38 MiB (1 cells, 64 layers) <- Gated-DeltaNet 狀態，不隨 context 成長
sched_reserve:  ROCm0 compute buffer   =   488.00 MiB
srv [spec] estimated memory usage of MTP context is 1512.00 MiB
```

ROCm0 合計約 **45,346 / 110,456 MiB**，剩約 65 GB。

**每 token 64 KiB**（16 層 × 4 KV heads × `n_embd_head_k = 256` × 2(K+V) × 2 bytes）。
我事前估 32 KiB 是錯的 —— 假設 head_dim = 128，實際是 256，**差兩倍**。
架構的 3:1 hybrid 被 log 證實：64 層裡只有 16 層進 KV cache，其餘 48 層走
`llama_memory_recurrent`（1 cell、固定 1,047 MiB）。

### MTP acceptance：借來的參數對不上實測

```
draft acceptance = 0.45343 (185 accepted / 408 generated), mean len = 3.72
acc per pos = (0.897, 0.662, 0.456, 0.279, 0.250, 0.176)
pp 165.124 t/s   tg 13.938 t/s
```

用的是從 qwable UltraQuality 卡片借來的 `n_max 6 / p_min 0.0 / p_split 0.20`，
那份卡片在同型硬體上自報 **99.5%**。我們實測 **0.453**，而
`GRM-2.6-Plus_rocm7.bat` 記載的損益平衡是 0.65–0.70，Fable 實測 0.73–1.00。

**這是同一天第二次證明別人的數字不能當自己的證據**（第一次是 fixture 大小）。
per-position 說明原因：position 1 是 0.897，到 position 3 剩 0.456，position 6 只剩 0.176 ——
draft 太深。`n_max 2`–`3` 或關掉 MTP 應該更快，**未測**（那是速度變數，不在這輪的正確性量測範圍內）。

### 工具呼叫探測

兩個 sampler arm 交錯（ABAB），唯一變數是 repeat-penalty：卡片指定 1.05 vs 共同基準 1.0。
`--max-tokens 4096`（**偏離預設 32768**，因為這是 reasoning model，
64 tokens 的測試整批被思考吃光；4096 足夠而且把失控成本壓在可接受範圍）。

```
fixture-673tok   (2,610 bytes, sha a006ef98d9f8)  -> prompt 1,798 tok
   A 1.05  6/6      B 1.00  6/6      A 1.05  6/6      B 1.00  6/6      = 24/24

fixture-15308tok (55,422 bytes, sha 048e990c36d4) -> prompt 16,434 tok
   A 1.05  6/6      B 1.00  6/6      A 1.05  6/6      B 1.00  6/6      = 24/24
```

全部 `finish=tool_calls`、`name=read`、`args_len=36`、無洩漏。

**但這 48/48 不能拿來宣稱 Qwythos 比 Fable 好。** Fable 基線在同一區間也是滿分
（14,095 → 12/12、16,880 → 8/8、20,100 → 8/8），它開始掉是在 23,083 之後。
**兩邊同時觸頂**，那跟同時觸底一樣沒有資訊量 —— 清單 §4 那條規則的鏡像形式。
sampler 對照同理：兩個 arm 都在天花板，這個設計目前分不出 1.05 與 1.0。

能成立的結論只有兩條：

1. Qwythos 在 harness 真實負載（每輪 15,287 tokens）**不會壞**，48/48
2. Laguna 明顯更差（4/12，且累積請求後退化到 0/24）

要分辨 Qwythos 與 Fable，必須量在 Fable 真正會壞的 23,077 / 26,048。**進行中。**

一個順帶量到的、對 prompt 預算有用的值：fixture 673 → prompt 1,798，
fixture 15,308 → prompt 16,434，兩邊都是 **+1,125 tokens** ——
那是 13 個 tool 定義加 user 訊息加 template 的固定成本。

一個尚未成為結論的觀察：rep-pen 1.05 在輕負載下輸出明顯更長
（12 次平均 274 tokens vs 1.0 的 218，差約 26%）。它想得更久。要當結論需要專門的對照。

---

## 八、Qwythos vs Fable：逐位元組相同的 fixture，顯著

### 這是怎麼做出來的

一個意外的便利：Qwen3.5 與 Qwen3.6 同族 tokenizer，同一組釘死來源產出的 fixture
**sha256 完全相同**（`048e990c36d4` 與 `f41338e59ce8`）。所以兩個模型吃的是同一個檔案，
不是「差不多大小的兩個檔案」—— 這正是 2026-07-29 做不到、因而全盤作廢的那件事。

Fable 側的條件：與本機啟動腳本相同的旗標、`--chat-template-file` 指向
qwen3.6-froggeric-v21.3（`/props` 第一行已確認）、**先灌 10 個短請求暖機**
（暖機狀態是交接檔記載的最大未解釋變異，不註明就不可比）、
`rep-pen 1.0`（Fable 的 MTP 硬性要求）、`--max-tokens 4096`（與 Qwythos 那批相同）。

```
15,308 tok  sha 048e990c36d4   Qwythos 24/24   Fable 0/8    Fisher p = 9.5e-08
23,077 tok  sha f41338e59ce8   Qwythos  8/8    Fable 0/8    Fisher p = 1.6e-04
合併                            Qwythos 32/32   Fable 0/16   Fisher p = 4.4e-13
```

15,308 是 harness 真實每輪負載。**Qwythos 32/32，Fable 0/16。**
這是兩天來第一個顯著的結果，也是第一次「單一變數、同一引擎、同一檔案」的模型比較。

Fable 今天 32 次全失敗的形狀：

```
markup-leak  10   <tool_code>{'name':'read_file'...}</tool_code>、<tool_code_name>…
truncated     5   撞 4096 上限仍在生成
timeout       7   900 秒（另一批用 32768 上限時）
no-call       8   含 capability-denial 與 fabricated-completion
```

模型發明了 `read_file`、`ReadFile`、`<tool_code_name>`、`<tool_code_parameters>` ——
Pi 只有 bash/edit/find/grep/ls/read/write，而 `<tool_code>` 也不是 froggeric v21.3 教的格式。

順帶量到一個未預期的差異：**Fable 需要數千個輸出 token，Qwythos 只要幾百個。**
Qwythos 的乾淨回合輸出 163–413 tokens；Fable 有 5 次撞到 4096 還沒講完、1 次到 2,627。
這也解釋了為什麼 `--max-tokens` 的取值對 Fable 影響巨大、對 Qwythos 完全不影響。

### 舊的 Fable 基線整條作廢

交接檔裡那條階梯（`671→12/12、14,095→12/12、16,880→8/8、20,100→8/8、23,083→6/8、26,052→6/8`）
**不能再當參照點**，有兩個獨立的理由：

1. **它是用會把逾時丟出分母的儀器量的。** 今天 16 次裡有 7 次逾時；照舊規則那 7 次會消失，
   0/16 會被記成看起來體面的數字。
2. **光是計數方式解釋不了差距。** 舊基線在 14,095 是 12/12，今天同尺寸同條件 0/8。
   最可能的變數是舊基線用 `max_tokens 32768`，讓漫長漫遊最終仍然產出呼叫；
   但無論原因為何，那條階梯已經不可信。

連帶影響：交接檔第 69 行「約 9% 的回合會拒絕或捏造」**是低估**，
而「這個比率在 671 到 26,052 tokens 之間量不出差別」建立在被污染的分母上。
昨天那次撤回（規模階梯沒有懸崖）**本身仍然正確**——那些配置比較確實無效——
但現在連基線都要用修好的儀器重跑，才能回答「規模到底有沒有懸崖」。

**這是同一個教訓的第三次現身：儀器把失敗變成缺席，而缺席看起來就像成功。**
第一次是 fixture 大小、第二次是逾時記成 error，第三次是前兩者的後果回頭污染了參照點。

### 機制問題：兩次都答不出來，停手

假設是「harness 注入的規則與 user 請求競爭注意力」，來自 26k 那次唯一的失敗
（`Read RULE 8 + RULE 10 — need verification first:`）。設計是同尺寸、同時間窗、ABAB 交錯，
唯一變數是填充物形狀（`--sources rules` vs `--sources neutral`）。

```
23,077 tok   rules 0/8   neutral 0/8   p = 1.0
15,308 tok   rules 0/8   neutral 0/8   p = 1.0
```

**兩次都是兩邊同時觸底**，正是清單 §4 那條規則要擋的情況。這個對照沒有回答任何事。

停手的理由寫下來，免得下次又試第三遍：**兩個模型都沒有可用的工作區間。**
Fable 在 15k–23k 全在地板上，Qwythos 到 41k 全在天花板。要研究這個機制，
需要先造出一個**能穩定產生部分失敗**的設定（例如刻意削弱的模型、或把工具描述改差），
否則再多樣本也只會得到 p = 1.0。

---

相關文件：
[2026-07-29 交接](2026-07-29-handoff.md) ·
[換模型驗收清單](2026-07-29-model-swap-checklist.md) ·
[失效形狀與 prompt 預算復盤](2026-07-29-tool-call-failure-modes-and-prompt-budget.md) ·
[docs/KNOWN_ISSUES.md](../KNOWN_ISSUES.md)
