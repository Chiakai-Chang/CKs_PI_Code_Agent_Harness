# 為什麼 harness「很零碎、難以驗證有沒有幫助」:一個空變數與 125 個 session(2026-08-16)

擁有者的三個觀察,原話:

1. 「若跨出此資料夾運行,pi 根本不知道 C.A.S.E 框架是什麼,他就開始到處亂搜尋」
2. 「然後為了要復盤他會回到本資料夾找 verify.py」
3. 「看起來不確定有沒有妥善使用 skills,整體感覺好像 harness 做的很零碎且難以驗證有沒有幫助」

**前兩個有單一根因,而且是我們自己造成的。第三個可以量,答案不好看但是明確的。**

---

## 一、前兩個觀察:`$PI_HARNESS_ROOT` 一直是空的

### 現象

Session `01a004bc-e2ea-794b-9bbc-eaed6733a063`(2026-08-15,cwd
`D:\MyProject\test-20260813-cyber-patrol`,與本 repo 無關的專案):

| 項目 | 值 |
|---|---|
| user 訊息 | 6 |
| assistant turns | 188 |
| tool calls | 224 |
| **碰到 harness 路徑的呼叫** | **41(18%)** |
| 開啟過的 SKILL.md | 2(都是 `Local-Agent-Workspace`) |

第 1 則 user 訊息**就是 `/case` 這個指令的內容**,它自己寫著:

```bash
python "$PI_HARNESS_ROOT/external/Local-Agent-Workspace/scripts/bootstrap.py" .
```
> 建完之後讀 `$PI_HARNESS_ROOT/external/Local-Agent-Workspace/SKILL.md`,那是協定本體。

模型第 2 個動作就是去確認那個變數:

```
call bash  pwd; echo "--- PI_HARNESS_ROOT ---"; echo "[$PI_HARNESS_ROOT]"
res        /d/MyProject/test-20260813-cyber-patrol
           --- PI_HARNESS_ROOT ---
           []
```

**空的。** 於是它靠猜絕對路徑去找 harness,找到之後把協定本體、`bootstrap.py`、
`verify.py` 一路讀進來 —— 第 12 到 19 個呼叫全部在本 repo 裡。

**所以「他就開始到處亂搜尋」不是模型亂跑,是 harness 叫它去的,而且沒有給它地址。**

### 根因

`scripts/restore.py:944` 寫了:

```python
settings["env"]["PI_HARNESS_ROOT"] = REPO_ROOT.replace("\\", "/")
```

而 `pi-rules/AGENTS.md:21` 對讀者說「the `PI_HARNESS_ROOT` env var is injected by
`scripts/restore.py`」。

**兩句都不成立。** 安裝版 `core/settings-manager.d.ts` 第 66–116 行的 `Settings`
介面**沒有 `env` 這個欄位**,執行期也沒有任何地方讀它。
那是一個 zombie config —— 正是本 repo 自己明文禁止的東西
(「Never register mock or empty extension files」的同一條精神)。

**它為什麼活了這麼久:每一次稽核打開 `settings.json` 都看得到那個值,然後就停在那裡。**
配置存在 ≠ 送達,這一整個月已經是第四次以不同形狀出現。

### 波及範圍

依賴這個變數的指示文件(不含 `external/`):

```
pi-skills/commands/case.md                     4 處
pi-rules/AGENTS.md                             1 處
pi-skills/core/hello-reflect/SKILL.md          1 處
pi-skills/optional/camofox-stealth/SKILL.md    3 處
pi-skills/optional/camofox-stealth/commands/browse.md  3 處
```

**十處指示,全部指向一個空字串。**

### 修法

`skill-namespace-guard` 在註冊時設 `process.env.PI_HARNESS_ROOT`。
為什麼這樣可行,是機械的而不是猜的:bash 工具**每次呼叫**都用
`getShellEnv()` 重建環境,而它展開 `process.env`
(安裝版 `utils/shell.js:103`,由 `core/tools/bash.js:119` 的
`resolveSpawnContext` 呼叫)。擴充跑在同一個行程裡。

三件配套:

* **驗證過才輸出**。`package.json` 出貨時是 `"root": "TODO_SET_BY_RESTORE"`,
  restore 安裝時才 patch。未 patch 的副本會輸出那個佔位符,而
  **一個錯的路徑比空字串更糟,因為模型會照著做**。所以要求該目錄底下同時有
  `pi-extensions/` 與 `pi-skills/`,兩個候選都不合格就**維持不設定**
* **不覆寫操作者自己 export 的值**
* **`restore.py` 改為 `settings.pop("env", None)`**,把已安裝的殭屍區塊清掉,
  免得它繼續看起來像一個能用的設定
* **`AGENTS.md` 改寫**:空值的時候要**停下來講**,不要靠猜路徑去找 harness,
  更不要離開被指派的專案

### 驗證(三層)

```
1. 單元(repo 副本)  tests/test_harness_root_env.py — 7 條,含子行程讀回、正斜線、不覆寫
2. 確定性(安裝副本)  載入 ~/.pi/agent/extensions/skill-namespace-guard/index.ts
                     before: ""  ->  after: "D:/MyProject/CKs_PI_Code_Agent_Harness"
                     child : "D:/MyProject/CKs_PI_Code_Agent_Harness"
3. 真實 Pi session   printf "%s" "$PI_HARNESS_ROOT" > root.txt  ->  3 個 tool call
                     root.txt 內容 D:/MyProject/CKs_PI_Code_Agent_Harness(正斜線 = 修法路徑)
```

**第一次的 live 探針是無效的,記在這裡。** 問題問成
「Run exactly this one bash command and then stop: echo "ROOT=[$PI_HARNESS_ROOT]"」,
模型回了 `` `ROOT=[D:\MyProject\CKs_PI_Code_Agent_Harness]` ``,
而 session 只有 5 筆記錄、**0 個 tool call** —— 它**捏造了輸出**。
反斜線就是識破它的線索:修法路徑只會產生正斜線。
換成「寫進檔案」之後才拿得到真證據。
**這條本身是一個發現:新模型會編造指令結果,而回覆看起來完全正常。**

---

## 二、第三個觀察:技能到底有沒有在幫忙

方法:`~/.pi/agent/sessions/**/*.jsonl`,排除 `Temp/` 與 scratchpad(探針),
只算 `message.role == "assistant"` 的 `toolCall`,參數路徑含 `.../<name>/SKILL.md`
才算「模型真的去讀了那個技能」。

```
真實專案 session   125 個,tool calls 4176
曾經開過任一技能的 session   15 / 125  (12%)
```

拆成兩邊看更清楚:

| | session | tool calls | 有開過技能 | 碰到 harness 路徑的呼叫 |
|---|---|---|---|---|
| harness 自己 | 72 | 1344 | 5 | 67(4%) |
| **其他專案** | **53** | **2832** | **10(19%)** | **218(7%)** |

**兩個數字回答了擁有者的問題:**

1. **技能層到達率約 12–19%。** 八成的工作沒有碰到任何方法論技能。
   這與 2026-08-13 的
   [skill-layer-reachability](2026-08-13-skill-layer-reachability.md)
   結論一致(45 個註冊技能,38 個從未被打開),只是換成用 session 當分母。
2. **在別人的專案裡工作時,7% 的呼叫花在 harness 目錄。**
   擁有者回報那個 session 的 18% 不是特例,是這個分布的極端值。
   而 CLAUDE.md 目前還寫著「真實 session 228 次呼叫碰到 harness 1 次」——
   **那個基準已經過期**,它取樣的是 `/case` 指令存在之前的時期。

**「零碎」的感覺是準確的,而且可以指名:** 一個把協定本體、bootstrap 腳本與 verifier
都放在 harness 裡、再用一個沒有值的變數去指路的設計,必然讓每個專案的工作都被扯回 harness。
修掉變數只解決「找不到」,**沒有解決「協定本體不在專案裡」** —— 後者是設計問題,見下。

---

## 三、這份量測沒有回答的事

* **修好變數之後,7% 會降到多少?** 不知道。需要修後累積的真實 session。
  已寫成觸發條件:再累積 ≥10 個其他專案的 session,重跑本文的查詢。
* **技能到達率 12% 是不是問題?** 這份量測只說到達率,沒說「該到達卻沒到達」。
  一個一行改動的請求不需要方法論技能,把它算成失敗是錯的。
  要判定必須先分類請求形狀,而 `report-task-shapes.py` 就是為此存在的。
* **`/case` 應該把協定本體複製進專案,還是繼續遠端引用?** 這是設計取捨,
  不是量測結果,留給下一輪。

---

## 可直接重跑的指令

```bash
# 那個 session 的形狀
python scripts/mine-session.py 01a004bc-e2ea-794b-9bbc-eaed6733a063

# 技能到達率與 harness 觸碰率(本文兩張表)
python - <<'PY'
import json,glob,os,re
root=os.path.expanduser(r'~/.pi/agent/sessions')
real=[f for f in glob.glob(os.path.join(root,'*','*.jsonl'))
      if 'Temp' not in f and 'scratchpad' not in f.lower()]
own=[f for f in real if 'CKs' in f and 'Harness' in f.replace('_','-')]
for name,fs in (("harness",own),("other",[f for f in real if f not in own])):
    calls=0; withskill=set(); touch=0
    for f in fs:
        for r in (json.loads(l) for l in open(f,encoding='utf-8') if l.strip()):
            m=r.get('message')
            if not isinstance(m,dict) or m.get('role')!='assistant': continue
            for b in (m.get('content') or []):
                if isinstance(b,dict) and b.get('type')=='toolCall':
                    calls+=1; a=json.dumps(b.get('arguments'),ensure_ascii=False)
                    if re.search(r'[\\/][\w.-]+[\\/]SKILL\.md',a): withskill.add(f)
                    if 'CKs_PI_Code_Agent_Harness' in a: touch+=1
    print(name, len(fs), calls, len(withskill), touch)
PY
```

---

## 相關

* 前一份量測:[2026-08-14 postmortem](2026-08-14-session-019ffbdd-postmortem.md)
* 技能層可達性:[2026-08-13-skill-layer-reachability.md](2026-08-13-skill-layer-reachability.md)
* 帳本:[PROGRESS.md](../../PROGRESS.md)
