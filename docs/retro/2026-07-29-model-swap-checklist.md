# 換模型驗收清單（2026-07-29 建立）

背景見 [2026-07-29-tool-call-failure-modes-and-prompt-budget.md](2026-07-29-tool-call-failure-modes-and-prompt-budget.md)。

**這份清單存在的理由**：2026-07-29 當天做的模型比較與引擎比較**全部作廢**，
因為 fixture（23,280 tokens）比要模擬的對象（harness 真實每輪 15,287）重了 50%，
落在門檻之上——那裡所有配置都會壞，於是每個比較都得到「沒有差別」。
清單裡的每一條都是那天買到的，特別是 §2 的「fixture 大小要對齊真實負載」
與 §4 的「兩邊都必須落在非地板區」。

已完成、可直接沿用的部分：`Qwen3.6-27B-Fable-Fusion-711` 已下載並跑得起來
（`C:\models\FableFusion-711-AMD_rocm7.bat`，載入與 template 都驗證過），
規模階梯（§3 基線）也是用它量的。**尚未做的是「與 GRM 的有效比較」。**

---

## 0. 前置

* `C:\models\FableFusion-711-AMD_rocm7.bat` 已實跑驗證（`/props` 回報正確的
  `model_path` 與 `qwen3.6-froggeric-v21.3`）。
  它修掉了舊 `FableFusion-711_HIP.bat` 的三個問題：指向不存在的 BF16 mmproj、
  `-ctk/-ctv q8_0`、缺 `--chat-template-file`。
* **server 啟動後先暖機再量測。** 剛啟動與運行兩小時的同一台 server，
  同一份 fixture 量到 0/12 與 6/8。暖機是目前最大的未解釋變異來源。
* **一次只動一個變數**：要嘛換模型、要嘛換引擎，不要一起。

## 1. 啟動並確認載到的東西

```bash
curl -s http://127.0.0.1:8080/props > props.json
node -e 'const p=require("fs").readFileSync("props.json","utf8");const j=JSON.parse(p);
console.log(j.model_path);console.log((j.chat_template||"").split("\n")[0])'
```

* `model_path` 必須是那支新的 `...NEO-AMD-MTP-Q6_K.gguf`。
* 第二行必須是 `{%- set template_version = "qwen3.6-froggeric-v21.3" %}`。
  若不是，`--chat-template-file` 沒生效——llama.cpp 對這件事**不報錯**，會靜默用 GGUF 內建的
  stock Qwen3.6 template。

> 這支 GGUF 的內建 template 就是原廠 Qwen3.6 版：教的是
> `<tool_call><function=name><parameter=key>` 格式，且含 `raise_exception('No user query found in messages.')`——
> 純工具迴圈沒有 user 訊息時會直接炸。froggeric v21.3 修的正是這些。

* 載入中 `/props` 會回應但 `/v1/chat/completions` 回 503。**等到後者回 200 再開始量測。**

## 2. 釘死量測輸入，而且大小要對齊真實負載

兩條規則，第二條是 2026-07-29 花了一整天買到的：

1. system prompt 必須來自固定檔，不能指向工作區的活檔——寫報告會改動那些檔案，
   等於邊量邊改條件。
2. **fixture 的大小必須對齊要模擬的對象。** 當天的「重負載」是 23,280 tokens，
   而 harness 真實每輪只有 15,287；23k 在門檻之上，門檻之上所有配置都會壞，
   於是每個配置比較都得到「沒有差別」——那是 fixture 造成的假象。

所以先量目標，再造 fixture：

```bash
# 目標的真實值（Pi 實際送出的 system prompt）
PI_HARNESS_DUMP_PROMPT=/tmp/real-prompt.txt pi --print "Reply with exactly: OK"

# 至少三個點：乾淨區、目標值、門檻區
#   乾淨區 ~14k、目標 ~15k、門檻 ~23k
# 填充物要與工作無關（虛構文件即可），否則「大小」與「內容」會混在一起
```

之後每次比對都用**同一組**檔案。要換內容就換檔名，不要就地修改。

## 3. 跑探測

```bash
node scripts/probe-tool-calls.mjs --system /tmp/sys-light.txt --tools 2  --repeats 3 \
     --model fable-fusion-711
node scripts/probe-tool-calls.mjs --system /tmp/sys-heavy.txt --tools 13 --repeats 6 \
     --model fable-fusion-711
```

`--target` 指的檔案**不能出現在 system prompt 裡**，否則「我已經有了」是正確答案、
卻會被記成失敗（這個坑踩過一次）。

判讀：

| shape | 意思 |
|---|---|
| `clean` | `finish_reason=tool_calls`、工具名正確、無標籤洩漏 |
| `capability-denial` | 宣稱沒有檔案系統存取權（工具清單裡明明有 `read`） |
| `fabricated-completion` | 宣稱讀了但沒呼叫 |
| `markup-leak` | 標籤或 XML 洩漏進文字或參數 |
| `no-call` / `wrong-call` | 其他 |

**對照基線（Fable-Fusion-711，同一時間窗、已運行約兩小時的 server）**：

```
   671 tok  -> 12/12      14,095 tok -> 12/12      16,880 tok -> 8/8
20,100 tok  ->  8/8       23,083 tok ->  6/8       26,052 tok -> 6/8
```

同一份 23,280 fixture 在**剛啟動**的 server 上是 **0/12**。基線必須註明暖機狀態，
否則不可比。

## 4. 判定規則（先重現，再下結論）

* **兩邊都必須落在非地板區。** 若兩個配置都在門檻之上（或都在剛啟動的 server 上），
  結果會一起觸底，「沒有差別」是量測失效不是結論。當天的引擎與模型比較就是這樣作廢的。
* 至少在**乾淨區與目標值各比一次**；只在門檻區比等於沒比。
* **先原樣重跑一次**確認能重現，再下結論。當天有兩次 6/6 與 0/6 都沒重現。
* 只有 1–2 次差異 = 噪音。差距要大過已觀察到的窗間漂移（0/12 ↔ 6/8，接近滿幅）才算數。
* 拿到穩定改善後，再跑多回合工具鏈，那才貼近真實 session。
* 最後才是真的開 Pi 跑一輪，看兩個新守衛（Guard 5 repeat-call、Guard 6 fabricated-work）
  在實戰裡是否誤傷。它們目前只有單元測試，而且它們攔的形狀只在門檻之上才常見，
  所以要在長 session 裡驗，不是在乾淨的短 session 裡。

## 5. 引擎版本（獨立變數，今天就能測）

`C:\models` 有四套 binary，版本實測如下（2026-07-29）：

```
llama-bin-win-hip-radeon-x64     version: 10173 (e9fa0781f)   官方 HIP
llama-bin-win-vulkan-x64         version: 10173 (e9fa0781f)   官方 Vulkan
llama-bin-win-rocm-x64           version: 9976  (e3546c794)   官方 ROCm（舊）
llama-bin-win-rocm7-gfx1151      version: 1     (91d2fc3)     lemonade gfx1151
```

lemonade 那版有自己的編號（`version: 1`），不能跟 ggml-org 的 `bNNNNN` 直接比；
官方兩版則明確是 **b10173**，也就是含 `b10156` 的
**Disable -ffast-math on HIP**（commit `91f8c9c`）。

**這個對照 2026-07-29 跑過，結果作廢，不是「無差別」**：

```
lemonade 91d2fc3        + GRM Q6_K，23,280 tok，新啟動 server  ->  1/12
官方 HIP b10173         + GRM Q6_K，同上                       ->  0/12
```

兩邊都在門檻之上、又都是剛啟動的 server，也就是**同時觸底**。這種條件下
1/12 對 0/12 分辨不出任何東西。要重做就照 §2 造對齊過的 fixture、
在暖機後的 server 上，於乾淨區與目標值各比一次。

取捨（若重做且真有差）：lemonade 版是這台機器的 PP 冠軍（`GRM-2.6-Plus_rocm7.bat`
註解記錄 PP 320 t/s vs 官方 HIP 264，Vulkan 145）。

**引擎與模型分開測。** 兩個變數一起動又是一次白測。

## 6. 換模型後要一起改的

* `pi-config/models.json` 與 `pi-config/settings.json` 的 `defaultModel`（兩個都是 gitignore 的本機檔，
  目前彼此不一致：settings 指 Q4_K_M，models.json 只宣告 Q6_K）。
* llama-server 的 `--alias` 決定 Pi 要用哪個名字；alias 對不上時 Pi 照樣送請求，
  server 回的是它實際載入的模型——**狀態列的模型名不能當證據**。

## 7. 2026-07-30 追加的四條（Laguna 那一輪買到的）

完整脈絡見 [2026-07-30 復盤](2026-07-30-laguna-abandoned-and-strix-halo-survey.md)。

1. **fixture 用 `scripts/make-probe-fixture.py` 產生，不要手工拼。**
   它從釘死的 40 字元 commit 產生、寫 sha256 manifest。而且要記住：**fixture 由 bytes 釘死，
   token 數是「(fixture, 模型) 配對」的性質** —— 不同 tokenizer 下「15,287 tokens」不是同一個檔案。
   跨模型比較要比 sha256。

2. **每個模型跑兩組取樣：卡片指定的，以及共同基準。** 調查過的六份 model card
   沒有兩份取樣相同（temp 0.6/0.9/1.0、top_k 20/60、repeat 1.0/1.05、甚至 presence 1.0）。
   只用共同取樣會把每個模型推出它被調校的區間，那本身就是製造「沒有差別」的方式；
   只用卡片取樣則把取樣差異混進模型差異。**兩組都報。**

3. **量測前把所有 server 端狀態機制關掉。**
   `--cache-ram 0`（prompt cache 預設 8192 MiB）、`--ctx-checkpoints 0`、
   `--checkpoint-every-n-tokens -1`。同一份 fixture、同一台 server，
   跑了幾十個請求之後從 4/12 掉到 0/24；`cache_prompt:false` 關不掉 server 層那一份。
   這比「暖機」更可能是 0/12 ↔ 6/8 的真正變數（**尚未驗證**）。

4. **失控回合要有上限。** `probe-tool-calls.mjs` 的 `--max-tokens`。
   EOG 有問題或思考失控的模型，每個沒呼叫工具的回合都會跑到上限；
   22 t/s 下 32768 tokens 是 25 分鐘一次，一批量不完。
   逾時與撞上限都算 **fail**，不是 error —— 記成 error 會讓最容易失敗的案例系統性地離開分母。
