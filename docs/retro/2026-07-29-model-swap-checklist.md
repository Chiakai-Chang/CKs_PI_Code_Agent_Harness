# 換模型驗收清單（2026-07-29 建立）

背景見 [2026-07-29-tool-call-failure-modes-and-prompt-budget.md](2026-07-29-tool-call-failure-modes-and-prompt-budget.md)。
`grm-2.6-plus` 在本 harness 的 prompt 規模下重負載 0/6 乾淨（Q4_K_M 與 Q6_K 皆然），
下一步是換 `Qwen3.6-27B-Fable-Fusion-711`（DavidAU，AMD/MTP Q6_K 變體）比對。

**這份清單存在的理由**：上一輪我用 n=6 的單向結果宣告了一個重現不出來的根因。
換模型比對很容易再犯同一個錯，所以步驟裡把「釘死輸入」和「先重現」寫成硬性要求。

---

## 0. 前置

* GGUF 下載完成（`*.gguf.aria2` 消失才算完成，24 GB）。
* `C:\models\FableFusion-711-AMD_rocm7.bat` 已備妥（未實跑驗證）。
  它修掉了舊 `FableFusion-711_HIP.bat` 的三個問題：指向不存在的 BF16 mmproj、
  `-ctk/-ctv q8_0`、缺 `--chat-template-file`。
* 決定要不要先更新 llama.cpp（見第 4 節）。**一次只動一個變數**：
  要嘛先換模型、要嘛先更新引擎，不要一起。

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

## 2. 釘死量測輸入

探測腳本的 system prompt 必須來自固定檔，不能指向工作區的活檔——
寫報告會改動那些檔案，等於邊量邊改條件。

```bash
# 輕負載基線
printf 'You are a coding agent working in D:/MyProject/CKs_PI_Code_Agent_Harness.\n' > /tmp/sys-light.txt

# 重負載：用 git object 釘死，不要用工作區的檔案
git show HEAD:CLAUDE.md            >  /tmp/sys-heavy.txt
git show HEAD:pi-rules/AGENTS.md   >> /tmp/sys-heavy.txt
git show HEAD:docs/KNOWN_ISSUES.md >> /tmp/sys-heavy.txt
git show HEAD:README.md            >> /tmp/sys-heavy.txt
```

之後每次比對都用**同一份**檔案。要換內容就換檔名，不要就地修改。

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

**對照基線（grm-2.6-plus，同條件）**：

```
輕負載（504 tok、2 工具）      ->  3/3 clean
重負載（23,284 tok、13 工具）  ->  0/6 clean
```

## 4. 判定規則（先重現，再下結論）

* 重負載跑出 **≥5/6 clean** 才值得往下看；**先原樣再跑一次**確認能重現。
  上一輪就是 6/6 沒重現，害我寫了個相反的結論。
* 只有 1–2 次 clean = 噪音，不是改善。
* 拿到穩定改善後，再跑多回合工具鏈（grm 基線 1/7），那才貼近真實 session。
* 最後才是真的開 Pi 跑一輪，看兩個新守衛（Guard 5 repeat-call、Guard 6 fabricated-work）
  在實戰裡是否誤傷。它們目前只有單元測試。

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

這使「HIP 的 `-ffast-math` 是否參與了重負載下的品質崩壞」變成**可直接對照的實驗**：
同一個 GGUF、同一份釘死 fixture、同一組取樣參數，只換 binary 目錄：

```
C:\models\llama-bin-win-rocm7-gfx1151   (91d2fc3, 目前主力)
C:\models\llama-bin-win-hip-radeon-x64  (b10173, 含 -ffast-math 修正)
```

取捨：lemonade 版是這台機器的 PP 冠軍（`GRM-2.6-Plus_rocm7.bat` 註解記錄
PP 320 t/s vs 官方 HIP 264，Vulkan 145）。若官方 HIP 的乾淨率明顯較高，
慢一點是划算的；若兩者一樣爛，就確定跟這個 commit 無關，可以收掉這條線。

**引擎與模型分開測。** 兩個變數一起動又是一次白測——這一天已經因此白跑過一輪。

## 6. 換模型後要一起改的

* `pi-config/models.json` 與 `pi-config/settings.json` 的 `defaultModel`（兩個都是 gitignore 的本機檔，
  目前彼此不一致：settings 指 Q4_K_M，models.json 只宣告 Q6_K）。
* llama-server 的 `--alias` 決定 Pi 要用哪個名字；alias 對不上時 Pi 照樣送請求，
  server 回的是它實際載入的模型——**狀態列的模型名不能當證據**。
