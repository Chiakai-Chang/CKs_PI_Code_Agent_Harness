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

後兩種是本次新增 Guard 5 / Guard 6 的理由。第三種在重負載下是**最常見**的一種——
量測顯示 23,284 token prompt + 13 工具時，Q6_K 與 Q4_K_M 都是 0/6 乾淨。

### 變數是 prompt 規模，不是量化

```
Q6_K   輕負載（504 tok、2 工具）      ->  3/3 乾淨
Q6_K   重負載（23,284 tok、13 工具）  ->  0/6 乾淨
Q6_K   多回合（4 回合工具鏈）         ->  1/7 乾淨
Q4_K_M 輕負載                        ->  3/3 乾淨
Q4_K_M 重負載                        ->  0/6 乾淨
```

排除掉的混淆變數（各自單獨測試）：draft KV 量化、`--rope-freq-base`、`top_k`。三個都無效。

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
| `docs/KNOWN_ISSUES.md` | 新增兩節，含一段「初稿結論是錯的」的保留紀錄 |
| `C:\models\GRM-2.6-Plus_rocm7.bat` | 補 `--chat-template-file`（repo 外，未版控） |

`python -m unittest discover -s tests` → 352 tests OK。

---

## 五、還沒解決 / 下一步

1. **原始症狀還在。** 重負載下模型拒絕或捏造，兩個新守衛只是讓它被看見並被糾正，不是治好它。
2. **唯一被重現過的槓桿是砍 prompt。** 目前 15,287；再往下要動 `skillTiers.core` 那 20 個方法論技能，
   與 CLAUDE.md 的「方法論優先」衝突，屬於取捨。
3. **兩個新守衛只有單元測試**，沒有真實 session 驗證。
4. 換模型測試（Qwen3.6-27B-Fable-Fusion-711）與 llama.cpp 更新——見
   `docs/retro/2026-07-29-model-swap-checklist.md`。
5. `pi-config/settings.json` 的 `defaultModel` 與 `models.json` 不一致（本機檔）。
