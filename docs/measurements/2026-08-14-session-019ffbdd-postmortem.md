# 換模型之後的第一個長 session:六個缺陷與一條根因鏈(2026-08-14)

擁有者的觀察:「我換了模型,發現問題不少,而且 skills 有些有提示但沒真的做,
例如『📝 偵測到新學習點 (1)。』一直出現,只有提示沒有意義。」

**結論先講:六個缺陷裡有三個共用同一條根因鏈 —— 模型換了,而
[換模型驗收清單](../retro/2026-07-29-model-swap-checklist.md) §1 沒有跑。**
那條清單第一句就是「確認 server 實際載到的 chat template」,理由寫得很清楚:
llama.cpp 對這件事不報錯。這次載到的 template 教模型用一套 XML 方言發工具呼叫,
而 Pi 用的是 OpenAI 原生 `tool_calls`。兩套協定同時在跑。

---

## 方法

* 主要證據:`~/.pi/agent/sessions/--D--MyProject-test-20260813-cyber-patrol--/2026-08-13T16-03-37-367Z_019ffbdd-6117-7b5f-a708-35af4d0dc622.jsonl`
  以 `scripts/mine-session.py` 讀,再用 `message.role` 逐筆過濾。
  不對整行 JSON 做子字串比對 —— 那個做法在 2026-08 給過三個確信但錯誤的數字。
* 服務層證據:`curl -s http://127.0.0.1:8080/props`(2026-08-14 取得,server 仍在運行)。
* 可達性證據:`pi-config/skill-catalog.json`、`pi-config/external-skills-manifest.json`、
  `pi-config/skill-conflict-report.json`、`~/.pi/agent/skills/` 的實際內容。
* 安裝一致性:`python scripts/verify-bridges.py` ——
  `13 bridges checked, 0 failure(s) found`,installed 與 repo 相符。**這次不是安裝漂移。**

## Session 的形狀

| 項目 | 值 |
|---|---|
| session | `019ffbdd-6117-7b5f-a708-35af4d0dc622` |
| cwd | `D:\MyProject\test-20260813-cyber-patrol`(真實專案,非 harness) |
| 模型 | `local-server / Muse-Glimmer-30B-Abliterated-Q6_K.gguf` |
| 時間 | 2026-08-13 16:03:37Z 至 22:36:06Z,約 6.5 小時 |
| user 訊息 | 11 |
| assistant turns | 122 |
| tool calls | 113 |
| errored tool results | 14 |
| 沒有 tool call 的 turn | 15(其中 1 個連文字都空) |

**批次崩了。** 每個 turn 的呼叫數是 `4/1/1/1/1/…`,113 次呼叫裡只有 3 個 turn 超過 1 次。
對照 2026-08-09 的 `019fe72a` 是 `2/4/4/4/4/1/1`。
這是換模型後的行為改變,本文件只記錄,不下因果結論 —— 樣本是 1。

到達模型的注入:`ecc advisory` 5、`routing note` 2、`goal restatement` 2、`compaction kit` 1。
`pi.sendMessage` 通道:`universal-tag-transformer` 3、`compact-continuation` 1。

---

## 根因鏈:ATEM template 對上 OpenAI 原生工具呼叫

### 現象

`</atem:日>` 這串字在 session 裡出現 **24 次**,全部在 `write` 工具的 `arguments` 裡。

* 24 次都黏在**最後一個參數的結尾**。所以每一份被寫出去的 `.md` 檔尾端都掛著這串垃圾。
* 有一次最後一個參數是 `path`:
  `"path":"investigation_2026_taiwan_local_election/.gitignore</atem:日>"`,
  錯誤是 `ENOENT: no such file or directory, mkdir '…\.gitignore<'`。
* 內容中段也被插入落單的 `日`:`- https日：...`、`- https於...`、`涵蓋全國22個縣日`。
* bash 參數被截成 `investigation_2026_tai567`,
  錯誤 `fatal: cannot change to 'investigation_2026_tai567': No such file or directory`。

### 根因

`/props` 回報的 `chat_template`(9,530 字元)裡有這段 macro:

```jinja
{%- macro render_atem(tc) -%}{%- set args = tc.function.arguments -%}
{%- if args is not mapping -%}{{- raise_exception('Onyx ATEM chat template requires
tool_call.function.arguments to be a dict (mapping); a JSON string cannot be parsed
in the HF jinja sandbox.') -}}{%- endif -%}
{{- '<atem:function_calls>\n<atem:invoke name="' + tc.function.name + '">\n' -}}
{%- for k, v in args.items() -%}{{- '<atem:parameter name="' + k + '">' -}}
… {{- '</atem:parameter>\n' -}}{%- endfor -%}
{{- '</atem:invoke>\n</atem:function_calls>' -}}{%- endmacro -%}
```

而且它把工具定義也用同一套方言教給模型:

> `You can invoke a function by writing a "<atem:function_calls>" block like the following:`
> `<atem:function_calls>\n<atem:invoke name="$FUNCTION_NAME">\n<atem:parameter name="$PARAMETER_NAME">$PARAMETER_VALUE</atem:parameter>…`

模型每寫完一個參數值,下一個 token 就是 `</atem:parameter>`。
`</atem:日>` 是這個結束標籤的殘缺解碼形式 —— **不是隨機亂碼,是 template 自己的語法**。
它出現在最後一個參數結尾,正是因為那是模型輸出裡它出現的位置。

同一份 `/props` 還顯示 `"modalities":{"vision":true,"video":true}`,代表 `--mmproj` 有在用。
上游有一個直接對應的已知問題:
[llama-server ignores `--chat-template-file` when `--mmproj` is provided](https://github.com/ggml-org/llama.cpp/issues/24189)
—— 給了 mmproj 就靜默改用 GGUF 內建 template。
社群整理的排錯頁也把「破掉的 template 會把 `<start_of_turn>` / `<end_of_turn>` 這類字面值漏進回覆」
列為典型症狀([Troubleshooting llama.cpp Tool Calls](https://netclaw.dev/troubleshooting/llama-cpp/))。

**這正是 2026-07-29 那份清單 §1 要防的事,原文寫著:**

> 若不是,`--chat-template-file` 沒生效 —— llama.cpp 對這件事**不報錯**,
> 會靜默用 GGUF 內建的 stock template。
> 這支 GGUF 的內建 template 教的是 `<tool_call><function=name><parameter=key>` 格式。

換了模型,清單沒有跑。**這是流程缺陷,不是程式缺陷。**

### harness 這邊的洞

`pi-extensions/yes-hooks-bridge/index.ts:468` 的 `FAKE_TOOL_CALL_PATTERN` 認得
`<invoke\b`、`<parameter\s+name=`、`<tool_call\b`、` ```bash ` 等等,**但認不得帶命名空間前綴的形式**:
`<atem:invoke` 不匹配 `<invoke\b`,`<atem:parameter name=` 不匹配 `<parameter\s+name=`。
一整套方言從所有偵測器底下穿過去。

同一條鏈也解釋了 `universal-tag-transformer` 為什麼會叫 3 次:
模型偶爾把整塊 XML 當文字吐出來,那時偵測器才勉強看到一點東西。

---

## 缺陷清單

### 一、`📝 偵測到新學習點` 是空的,而且它指的 skill 真的載不到

`pi-extensions/ecc-hooks-bridge/index.ts:457` 在 `turn_end` 呼叫
`ctx.ui.notify('📝 偵測到新學習點 (N)。', "info")`。
依本 repo 自己的結論(見 CLAUDE.md「Pi Extension Facts」),`notify` 只畫 TUI,**到不了模型**。
同一段第 458 行推了一條 advisory 說 `Use the hello-reflect skill…`,那條走
`before_agent_start` 有送到(mine 顯示 `ecc advisory` 5 次)。

但 `hello-reflect` 模型載不到:

* 不在 `~/.pi/agent/skills`(`scripts/restore.py:1186` 的 `managed_skills` 主動刪掉)
* 不在 `skillTiers.core`(23 個名字,無此名),所以被降級
* 不在這台機器的 `pi-config/skill-catalog.json`(102 筆,無此名)

而且不只它。**這件事 repo 自己的檢查早就知道,而且是紅的。**
`python -m unittest discover -s tests`(2026-08-14,harness `3f1ff85` + 未提交的工作樹):

```
Ran 1454 tests in 122.419s
FAILED (failures=2)
```

兩個失敗是**同一個缺陷的兩個出口**:

```
FAIL: test_every_demoted_local_skill_is_reachable
  (test_skill_catalog_staleness.TestTheRealCatalogWhenItExists)
AssertionError: … local skills demoted from native registration but absent from
the catalogue are reachable by no route at all; re-run
`python scripts/setup.py --mode restore`

FAIL: test_repo_as_shipped_passes (test_validate_config.TestValidateConfig)
FAIL: 18 local skill(s) are neither natively registered nor in the catalogue,
so nothing can reach them: …
```

**是 18 個,不是我先數的 14 個** —— 我只查了 `pi-skills/core`,檢查同時涵蓋 `optional`:

```
adversary-review  autonomous-experiment-guide  browser-automation-guide
contrarian-review  deep-research-guide  grilling-protocol
guardian-pipeline-guide  harness-factory-guide  hello-reflect
ide-intelligence-guide  minimal-prompt-guide  subagent-orchestration-guide
tool-repair-guide  workflow-os-guide
camofox-stealth  cua-commander  nothing-design  thinking-frameworks
```

**`thinking-frameworks` 在這份名單裡,而 CLAUDE.md 的方法論路由指名它**
(「一個有取捨的決定 → `thinking-frameworks` / `mece-autopilot` / `qiushi`」)。
這是同一個缺陷的第二個活體實例,而且它在專案的最上層指示裡。

**這條的教訓比缺陷本身重:守衛存在、守衛是紅的、遠端沒有人動它。**
`scripts/validate-config.py` 也印同一句話並回傳 1。
本次復盤在規劃階段一度打算「新增一支可達性檢查」——
那支檢查已經存在、已經在失敗、而且訊息裡連補救指令都寫好了。
**這是「先查既有再動手」那條規矩的自體版本:先跑自己的測試套件,再設計新的守衛。**

### 而且這是第三次

`tests/test_skill_catalog_staleness.py` 的檔頭把 **2026-08-04** 那次寫得清清楚楚:

> Measured on this machine, 2026-08-04, before any change here:
> `skill-catalog.json -> 104 entries, all under external/*, 0 from pi-skills`
> 所以 `hello-reflect`、`thinking-frameworks`、`grilling-protocol`、`camofox-stealth`
> 與另外十一個「registered nowhere and catalogued nowhere」。

**檢查寫了,原因沒查。** 而原因在 2026-08-14 用兩道指令就分岔出來了:

```
restore --auto --profile standard               -> 120 entries, hello-reflect: True,  validate 0 failures
restore --auto --profile standard --config-only -> 102 entries, hello-reflect: False, validate 1 failure
```

`--config-only` 的 early return 落在本地名單折入 catalog **之前**。
所以任何一次 config-only restore 都會把檔案默默改回壞的狀態。

**為什麼十天沒有人追:因為那條檢查印的補救「重跑 restore」真的有效。**
紅了就重跑、綠了就過去。
**一個有效的補救,比沒有補救更會藏住成因** —— 它把「為什麼會壞」換成了「怎麼修好」,
而後者每次都成功,於是前者永遠不會被問。

修法是把兩批合併搬進寫檔的**同一個運算式**(`merged_catalog_entries()`),
讓先後順序不再存在,也就沒有 early return 能把它們拆開。
防迴歸測試斷言的對象是**那個函式**,不是磁碟上的檔案 ——
磁碟狀態會被下一次 restore 修好,而那正是這個缺陷藏了十天的方式。

**機制(程式路徑已證,本機觸發為推論):**
`restore.py:1035` 的 `write_catalog` 先用「只有 external」的清單覆寫 catalog;
把本地降級那批折進去的 `merge_into_catalog` 在約 1236 行,
而 `--config-only` 的 early return 在 1175 行 —— **擋在中間**。
`skill-catalog.json` 與 `external-skills-manifest.json` 的 mtime 同為 `2026-08-13 23:58:08`,
而 catalog 缺的恰好就是本地那 14 筆。

把 catalog 複製到暫存目錄手動呼叫 `merge_into_catalog(path, tail)`:

```
lost []
total 116  hello-reflect present: True
```

**函式本身沒壞,是流程沒走到它。**

**還有三個附帶問題,都在同一段程式裡:**

1. `notify` 沒有去重(advisory 是 `"once"`,notify 不是),122 個 turn 就噴 122 次。
   這是擁有者實際看到的那個現象。
2. 每個 `turn_end` 都 `execSync` 起一個 python 行程,並遞迴掃過整個
   `~/.pi/agent/sessions`(這台機器上有 20 個 workspace 目錄)。
3. 它挑的是「全域 mtime 最新的 `.jsonl`」,**不保證是當前 session** ——
   同時開兩個 Pi 就會讀到別人的紀錄。這是一個歸因缺陷。

### 二、ECC GateGuard 的語意被通道反轉,而且改變了模型的下一步

`external/ecc/scripts/hooks/gateguard-fact-force.js` 是 **PreToolUse 的阻擋 hook**。
harness 把它的原文當成 advisory 貼在**已經成功**的 tool result 後面:

```json
"content":[{"text":"(no output)"},
           {"text":"[ecc-hooks] advisory (not command output):\nECC GateGuard: [Fact-Forcing Gate]\n\nBefore the first Bash command this session, present these facts:…"}]
```

模型的 thinking 逐字:

* `GateGuard requires facts. Let's present facts then retry.`
* `Maybe git init didn't work due to GateGuard. Let's try again with explicit.`

第二句是實害。那次 `git init` **成功了**
(`Initialized empty Git repository in D:/…/investigation_2026_taiwan_local_election/.git/`),
advisory 貼上去之後模型判定它失敗,接著在 call 75 到 102 之間燒掉約 28 次 bash
在 `git config` / `safe.directory` 上打轉。

另外,「Before the **first** Bash command this session」在同一個 session 觸發了 **2 次**
(16:18:50Z、22:26:20Z)。

**這是既有教訓的新形態。** repo 已經知道「移除選項的守衛必須配一個在選項回來時說話的東西」;
這次是反過來 —— **一個不移除任何東西的通知,被讀成了移除**。

### 三、`universal-tag-transformer` 把模型的輸出當成指令解析

第 3 則轉換訊息解析出來的 command:

```
git add README.md docs/
git commit -m "整理專案結構，新增 README.md 與 docs 指南"
commit fe56ec6
```

`commit fe56ec6` 是 git 的**輸出回顯**,不是指令。解析器把它撈進參數,
再用 `🔥【指令】：請你在此輪對話中【立即且只能】呼叫原生工具 'bash'` 命令模型照送。

這是既有教訓「Fixtures encode assumptions」的第 N 次複發:
解析器的 fixture 是人寫的乾淨程式碼區塊,而真實輸出裡指令與回顯是混在一起的。

### 四、`scripts/mine-session.py` 把別人的訊息算成 loop guard

(這條在擁有者的 working tree 裡,尚未 commit。)

`REFUSALS` 表把 `loop guard` 對到 marker `重複`。
整份 session 裡 `重複` 只出現 **3 次**,全部來自 `universal-tag-transformer` 自己那句
「(原文不在此重複,以免你再照著寫一次。)」。

所以報表印的 **`loop guard 3` 實際是 0**,而且它數的是另一個機制的訊息。
同一份報表已經正確地把 `universal-tag-transformer 3` 列在 customType 區塊 ——
**同一批訊息被數了兩次,掛在兩個機制名下。**

### 五、批次崩壞

113 次呼叫分佈在 122 個 turn。詳見上面「Session 的形狀」。
n=1,不下結論,列為待量。

### 六、14 個 errored tool result 的組成

| 類型 | 次數 | 說明 |
|---|---|---|
| `edit` 找不到/不唯一/空 oldText | 5 | 模型對自己剛寫的檔案做 edit 而字串不符 |
| `git` 相關 | 6 | `not in a git directory` ×4、`dubious ownership` ×1、`nothing to commit` ×1 |
| ATEM 標籤造成的路徑錯誤 | 2 | `.gitignore</atem:日>`、`investigation_2026_tai567` |
| Citation guard 拒絕 | 1 | **這一次是守衛正常工作**,見下 |

**Citation gate 是這個 session 裡唯一乾淨動作的機制。**
它拒絕了一份 1,344 字元、0 個網址、而 session 已開過 5 個頁面的報告,
並且把已開頁面的清單直接列給模型。這是「顯示你看到的,而不是他們該做什麼」那條教訓的正面樣本。

---

## 我一度判斷錯的一點,更正在此

我先前依 `~/.pi/agent/skills` 只有 16 個目錄,推論 23 個 core skill 有 20 個不見了。**錯的。**

`pi-config/skill-conflict-report.json` 的 `generatedAt` 是 `2026-08-13T16:03:38.755Z`
—— 正好是這個 session 開場的下一秒 —— 裡面 22 個 external skill 全部列出、`conflicts: 0`。
它們由 `skill-namespace-guard` 在 `resources_discover` **動態註冊**,不落地到 skills 目錄。
用目錄內容判斷可達性,量的是錯的東西。

**external 那批當時是好的。壞掉的只有本地降級那 14 個。**

這條記在這裡,是因為它本身就是一個可重複的量測陷阱:
**這個 harness 有三條技能註冊路徑(settings.skills、agent/skills 目錄、manifest 動態註冊),
任何只看其中一條的可達性判斷都會錯。**

---

## 與 Round 15 的關係

[Round 15](../mece/rounds/2026-08-13_round15_註冊了但沒有人叫它.md) 的結論是
「**註冊了,但沒有人叫它**」—— 45 個註冊技能,38 個從未被打開。

這份量測補上它下面那一層:**有一批技能連被叫的資格都沒有**。
Round 15 說過「蒸餾的 16 個核心技能有 15 個連註冊層都不在,只在 120 個名字的目錄層」;
本文件的新事實是 —— **在這台機器上,它們連目錄層都不在**。

兩件事合起來,技能可達性有三種失敗,必須分開處理:

| 層 | 失敗 | 本次證據 |
|---|---|---|
| **可達** | 既沒註冊也不在 catalog | 14 個本地 core skill |
| **可見** | 在 catalog 但只有名字,模型不知道何時用 | Round 15 的 120 個 |
| **被叫** | 註冊且有描述,但沒有機制點名 | Round 15 的 38 個 |

**一條 advisory 叫模型去用一個第一層就不存在的技能,是這次現象的完整解釋。**

---

## 可直接複製的重驗指令

```bash
# 1. session 的形狀
python scripts/mine-session.py 019ffbdd-6117-7b5f-a708-35af4d0dc622

# 2. 服務層實際載到的 template(換模型後第一件事)
curl -s http://127.0.0.1:8080/props > props.json
python -c "import json;t=json.load(open('props.json'))['chat_template'];\
import re;print(sorted(set(re.findall(r'<[^>\n]{1,40}>',t))))"

# 3. 技能可達性(三條路徑都要看)
python -c "import json,os;\
core=json.load(open('pi-config/harness-config.json',encoding='utf-8'))['skillTiers']['core'];\
cat={e['name'] for e in json.load(open('pi-config/skill-catalog.json',encoding='utf-8'))['skills']};\
inst=set(os.listdir(os.path.expanduser('~/.pi/agent/skills')));\
print([n for n in core if n not in cat and n not in inst])"

# 4. 安裝是否漂移
python scripts/verify-bridges.py
```

---

## 相關

* 換模型清單:[docs/retro/2026-07-29-model-swap-checklist.md](../retro/2026-07-29-model-swap-checklist.md)
* 技能層可達性:[docs/measurements/2026-08-13-skill-layer-reachability.md](2026-08-13-skill-layer-reachability.md)
* 本次的 MECE 復盤:[Round 16](../mece/rounds/2026-08-14_round16_模板換了而清單沒有跑.md)
* 上游問題:[llama.cpp #24189](https://github.com/ggml-org/llama.cpp/issues/24189)、
  [Troubleshooting llama.cpp Tool Calls](https://netclaw.dev/troubleshooting/llama-cpp/)
