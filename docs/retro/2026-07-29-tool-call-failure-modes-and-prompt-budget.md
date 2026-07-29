# 復盤：工具呼叫失效的三種形狀，與 prompt 預算的真實量測（2026-07-29）

起點是一份使用者貼上的 Pi session：模型連續以 `<read><path>…</path></read>` 描述工具呼叫，
transformer 糾正三次，loop guard 交還使用者，整個 session 報廢。

結束時修掉四個真缺陷、砍掉 9.9% 的每輪 prompt、加了兩個新守衛——
但**原始症狀沒有解決**，而且中途我自己犯了兩次「量測錯誤導致結論相反」的錯。
這份文件記錄的是後者，因為那才是會重複發生的部分。

---

## 一、最終確立的事實

### 失效有三種形狀，不是一種

| 形狀 | 特徵 | 誰看得見 |
|---|---|---|
| **標籤文字** | `<read><path>X</path></read>`，零真實呼叫 | `parseUniversalToolTag`（本次修好子標籤解析） |
| **參數失控** | 真實呼叫，`query` 塞 145,638 字元的 XML | `runawayArgumentGuard`（既有） |
| **拒絕／捏造** | `finish_reason=stop`、零呼叫、宣稱「已讀取」或「我沒有檔案系統存取權」 | **今天以前沒有任何守衛看得見** |
| **同呼叫迴圈** | 26 次一模一樣的 `read`，每次都成功 | **今天以前沒有任何守衛看得見** |

後兩種是本次新增 Guard 5 / Guard 6 的理由。第三種在 context 大到一定程度後是最常見的一種。

### 變數是 context 大小，不是量化、不是引擎、不是注入的內容

規模階梯（Fable-711，同一時間窗、同一台已運行約兩小時的 server，填充物與工作無關）：

```
   671 tok（原版 Pi 自己的 system prompt）      ->  12/12
14,095 tok（其中 13,930 是本 harness 的規則文字）->  12/12
16,880 tok                                     ->   8/8
20,100 tok                                     ->   8/8
23,083 tok（中性填充）                          ->   6/8
23,280 tok（repo 文件）                         ->   6/8   ← 與中性填充相同
26,052 tok                                     ->   6/8
```

**注入什麼不重要，注入多少才重要。** 把 harness 自己的規則文字塞到 13,930 tokens
仍然 12/12；同樣 23k，中性填充與 repo 文件的結果一模一樣。

**真正被排除的只有「注入內容」**——它是唯一在乾淨區（13,930 tok）與門檻區（23k）
都做過對齊比較的變數。其餘（權重量化、推論引擎、模型、draft KV 量化、`--rope-freq-base`、
`top_k`、`min_p`/`repeat_penalty`）都是在 23k、多半又在剛啟動的 server 上比的，
**兩邊同時觸底時的「沒有差別」不是結論，是作廢**。

**但還有一個比規模更大的未解釋變異：server 暖機狀態。** 同一份 23,280 fixture、
同一台 server、同一個模型，剛啟動 0/12、運行兩小時後 6/8；兩個模型各出現一次同樣模式。
對照實驗（新啟動 → 立刻量 → 暖機 → 再量）尚未執行。

### 真實 prompt 預算（`PI_HARNESS_DUMP_PROMPT` 量到的，不是推算）

```
  6446  <available_skills>   46%
  3923  AGENTS.md
  1418  CLAUDE.md
   644  Pi base / preamble
   620  web + deep-research guidance
   642  skill catalog（104 技能）
   274  case + mece bridge blocks
    90  native-tool protocol
 14055  systemPrompt（單輪 input 16,965）
```

原生註冊技能每個約 307 tokens，catalog 裡每個約 6 tokens。
`skillTiers` 只作用在 `external/*`，`pi-skills/core` 與 `optional` 整包複製進 agent dir，
完全繞過分層——修好後 60 → 42 個、單輪 input 16,965 → 15,287。

---

## 二、我犯的錯（這份文件的重點）

### 錯誤 0：fixture 從未對齊要模擬的對象——這一個讓其餘所有比較作廢

整天用的「重負載」fixture 是 **23,280 tokens**，而 harness 真實每輪是 **15,287**。
那個數字的來源只是「把幾份大文件串起來差不多這麼大」，我從沒回頭問它像不像目標。

後果不是「數字偏高一點」，是**每一個配置比較都失效**：23k 在門檻之上，
門檻之上所有配置都會壞，所以引擎、模型、量化比下來全部「沒有差別」——
那個「沒有差別」是 fixture 造成的，不是配置造成的。

發現它靠的是使用者一句「要不要跑原版 pi 看看，我懷疑是我們 harness 用壞了」。
原版 Pi 的 system prompt 只有 671 tokens，一次就成功呼叫工具。
那個對照逼出了規模階梯，階梯才顯示 15,287 落在乾淨區、23k 才是壞的。
**若不是這句話，我會繼續在門檻之上換配置，永遠得不到訊號。**

規則：**先量目標的真實值，再設計 fixture。** 一個「差不多這麼大」的負載，
量出來的是那個負載的性質，不是目標的性質。

### 錯誤 1：用 n=6 的單向結果宣告根因

Q6_K 重負載跑出 6/6 乾淨、Q4_K_M 同條件 0/6，我就寫了「權重量化才是變數，Q4_K_M 不堪用」。

那個 6/6 **重現不出來**。同一支腳本、同一台 server、用 `git show HEAD:` 還原出一模一樣的
23,284 token prompt，重跑 0/6。差別在輸出長度：6/6 那次每回合只生 76–93 token 就發出呼叫，
重跑時每回合生 587–964 token 的散文再拒絕。原因至今未查明。

**規則：根因宣告前必須先重現一次。** 尤其是「全對」或「全錯」這種漂亮結果——
它們最像證據，也最容易是噪音。

### 錯誤 2：量測工具讀著自己正在被修改的輸入

探測腳本的 system prompt 是用 repo 文件（含 `docs/KNOWN_ISSUES.md`）組出來的。
我把量測結果寫進 KNOWN_ISSUES，prompt 就從 23,284 漲到 24,393 token——
**寫報告這個動作本身改變了被量測的條件**。

**規則：量測輸入必須釘死。** 用 git object、或複製到 scratchpad，不要指向工作區的活檔。

### 錯誤 3：把「推算」當「量測」

第一版 prompt 歸因是「把候選檔案 tokenize 再相減」，結論裡有兩個錯誤：
以為 `CLAUDE.md` 沒被注入（其實有，1,418 tokens），
以為 `skill-catalog.json` 被整份注入（其實 bridge 只注入名稱清單，639 tokens）。

修法是加 `PI_HARNESS_DUMP_PROMPT=<file>`，把 Pi 實際送出的 prompt 倒出來。
**相減法不是量測，是假設的算術。**

### 錯誤 4（環境）：探測跑在 server 還在載入時

llama-server 載入中 `/props` 已經會回應，但 `/v1/chat/completions` 回 503。
探測腳本把 503 當成「0 個工具呼叫」記成失敗，整批數據作廢。

**規則：健康檢查要打真正要用的端點，不是隨便一個會回 200 的。**

### 這五個錯的共同形狀

錯誤 0 是「量錯對象」，1 是「樣本太小就下結論」，2 是「量測干擾被量測物」，
3 是「用推算冒充量測」，4 是「量到的是工具的 bug 不是被測物的性質」。

五個都不是關於模型或 harness 的知識問題，全部是**量測紀律**問題。
一天之內同一類錯誤犯五次，代表這不是失手，是預設行為：
拿到一個看起來合理的數字就往下推論，不先問「這個數字量的是什麼」。

對照組是唯一救得回來的機制——而今天真正有效的那個對照組（跑原版 Pi）是使用者提的，不是我。

---

## 三、環境層面的收穫

* **Pi 跑的是 `~/.pi/agent/extensions/` 的安裝副本，不是 repo 檔。**
  今天之前所有 bridge 改動 Pi 都沒吃到（38,797 vs 51,761 bytes），
  要 `python scripts/setup.py --mode restore` 才生效。改完 bridge 沒 restore = 沒改。
* **把 `~/.pi/agent/extensions/` 裡的目錄改名成 `_off_xxx` 不會停用擴充**，Pi 照載每個子目錄。
  要移出目錄才算停用。
* `--chat-template-file` 漏掉時 llama.cpp 靜默改用 GGUF 內建 template，不報錯。
  `GRM-2.6-Plus_rocm7.bat`（Q6_K 主啟動器）就漏了，等於修好的 template 從沒生效。
* Node 輸出重導到檔案是緩衝的，長時間背景跑的探測看不到中間結果——要嘛寫檔 flush，要嘛等結束。

---

## 四、落地的改動

| 檔案 | 改了什麼 |
|---|---|
| `pi-extensions/yes-hooks-bridge/index.ts` | 子標籤參數解析、Qwen 原生 `<function=>` 格式辨識、唯讀意圖代執行、Guard 5 repeat-call、Guard 6 fabricated-work、`PI_HARNESS_DUMP_PROMPT` |
| `scripts/restore.py` | `tier_local_skills()` / `merge_into_catalog()`：本機技能走同一套分層 |
| `tests/test_universal_tool_parser.py` | +24 測試（子標籤、代執行、兩個新守衛、prompt dump） |
| `tests/test_skill_tiers.py` | +4 測試（本機技能分層、catalog 合併） |
| `docs/KNOWN_ISSUES.md` | 新增兩節，含一段「前三版結論都是錯的」的保留紀錄 |
| `scripts/probe-tool-calls.mjs` | 可重複的探測器：釘死 system prompt 與全部取樣參數、分類失敗形狀 |
| `C:\models\GRM-2.6-Plus_rocm7.bat` | 補 `--chat-template-file`（repo 外，未版控） |
| `C:\models\FableFusion-711-AMD_rocm7.bat` | 新模型啟動器，修掉舊 bat 的三個問題（repo 外，未版控） |

`python -m unittest discover -s tests` → 352 tests OK。

---

## 五、還沒解決 / 下一步

1. **server 暖機是目前最大的未解釋變異**，比 context 大小的影響更大。
   對照實驗：新啟動 → 立刻量 n=8 → 灌一批短請求暖機 → 再量 n=8。尚未執行。
   若成立，`.bat` 或 harness 啟動流程應該加預熱步驟。
2. **真正的槓桿是控制 session 成長，不是再砍每輪注入。**
   每輪 15,287 落在乾淨區（16,880 仍 8/8），會越過 ~23k 門檻的是工具結果與回合累積。
   要動的是 compact 觸發點與工具輸出截斷上限。
   （「把 16,965 砍到 15,287 有助於此」的說法已撤回——兩個數字都在乾淨區。）
3. **兩個新守衛只有單元測試**，沒有真實 session 驗證。它們攔的形狀在門檻之上才常見，
   所以驗證要在長 session 裡做，不是在乾淨的短 session 裡。
4. 模型比較（GRM vs Fable-Fusion-711）在門檻之上做過、結論作廢；
   要重做就用對齊過的負載，見 `docs/retro/2026-07-29-model-swap-checklist.md`。
5. `pi-config/settings.json` 的 `defaultModel` 與 `models.json` 不一致（本機檔）。
