# 技能層到底有沒有在運作:165 個真實 session 的實測(2026-08-13)

擁有者的問題:「原本參考了這麼多 repo,其他有發揮作用嗎?為什麼幾乎感覺不到 superpowers?」

**答案:感覺不到是對的,而且可以量。技能不是沒裝,是沒有人叫它。**

## 方法

* 系統提示的**實際內容**:`PI_HARNESS_DUMP_PROMPT=<file> pi --print "hi" < /dev/null`
  (45,637 字元,2026-08-13,harness `71fc7b2`)
* **真實 session**:`~/.pi/agent/sessions/**/*.jsonl` 共 **165 個**,
  只計 `message.role == "assistant"` 的 `toolCall`,其參數路徑含 `.../<name>/SKILL.md`。
  這是「模型真的去讀了那個技能」的唯一證據,不是字串比對整行 JSON
  (那個做法在 2026-08 給過三個確信但錯誤的數字)

## 一、superpowers 是完整註冊的

系統提示裡的 `<available_skills>` 有 **45 個技能,每一個都有 `<name>` 與 `<description>`**,
superpowers 的 14 個全部在內,位置指向 `external/superpowers/skills/<name>/SKILL.md`。

**所以這不是接線缺陷。** 之前如果有人猜「大概沒註冊到」,那個猜測到此為止。

## 二、註冊 ≠ 被使用

165 個 session 裡,45 個已註冊技能中:

```
曾被打開過   7
從未被打開  38
```

從未被打開的 38 個(完整清單):

> case-framework, caveman, chrome-cdp, code-review, codebase-design,
> contradiction-analysis, design-an-interface, dev-browser, diagnosing-bugs,
> **dispatching-parallel-agents**, domain-modeling, **executing-plans**, find-skills,
> **finishing-a-development-branch**, git-guardrails-claude-code, graphify, grilling,
> hallmark, migrate-to-shoehorn, obsidian-vault, prototype, qa,
> **receiving-code-review**, request-refactor-plan, **requesting-code-review**, research,
> **resolving-merge-conflicts**, scaffold-exercises, setup-pre-commit,
> **subagent-driven-development**, **systematic-debugging**, tdd, **test-driven-development**,
> **using-git-worktrees**, **verification-before-completion**, **writing-skills**, yes,
> pi-planning-with-files*

粗體是 superpowers 的。**`systematic-debugging`、`test-driven-development`、
`verification-before-completion` —— 這三個正是使用者在別的專案裡最有感的東西,在這裡是 0 次。**

\* `pi-planning-with-files` 的註冊名與目錄名(`planning-with-files`)不同,
以目錄名計是 **6 次 / 5 個 session**,見下表。這個名字不一致本身在 2026-08-12 造成過一次
真實故障(每一條方法論路由都指向載不到的名字)。

曾被打開的:

| 技能 | 呼叫數 | session 數 | 誰叫它的 |
|---|---|---|---|
| `planning-with-files` | 6 | **5** | task-shape 路由器點名 |
| `research-task-routing` | 3 | 3 | 路由器自己 |
| `mece-autopilot` | 2 | 2 | mece bridge 點名 |
| `brainstorming` | 2 | 1 | 路由器點名 |
| `darwin-skill` | 12 | 1 | 單一 session,開發時讀的 |
| `agents-best-practices` | 12 | 1 | 同上 |
| `using-superpowers` / `writing-plans` | 各 1 | 1 | 單一 session |

## 三、規律很乾淨:**只有被機制當場點名的技能會被打開**

跨越多個 session 被打開的只有四個,而那四個**全部**有一個 bridge 在動作發生的當下說出它的名字:

* `planning-with-files`、`brainstorming` —— `task-shape-bridge` 的請求形狀路由
  (提示裡原文:*"Routes the work to brainstorming and pi-planning-with-files"*)
* `research-task-routing` —— 路由器本體
* `mece-autopilot` —— mece bridge

**其餘 38 個全部依賴「模型自己從 45 條描述裡挑一個」,結果是 0。**

這正是本 repo 早就寫下的那條(camofox 的教訓)——
**沒有被觸發的能力等於不存在** —— 只是這次量到了規模:45 個裡有 38 個。

## 四、蒸餾出來的 16 個核心技能,比 superpowers 還遠一層

| | 註冊(有描述) | 目錄(僅名稱) |
|---|---|---|
| superpowers 14 個 | ✅ | — |
| 蒸餾核心技能 16 個 | **15 個都不是** | ✅ 在 120 個名字的目錄裡 |

只有 `research-task-routing` 一個進了註冊層。也就是說,
「蒸餾 13 個頂級 repo」這件工作的產物,**目前放在比 superpowers 更難被看見的那一層**,
而它們同樣沒有任何機制會點名。

## 五、成本

`<available_skills>` 區塊 **19,885 字元 = 整份系統提示的 44%**。
其中 38 個技能在 165 個 session 裡從未被打開過一次。

**每一輪都在付這 44%,換到的是 7 個曾被用過的名字,而其中 4 個是靠 bridge 點名才被用的。**

## 六、參考:擁有者另一個專案(Viblux)裡的 superpowers 長什麼樣

**只讀,未修改任何檔案。** 那個專案裡的 superpowers **不是執行期機制,是產出物與入口文件**:

* `docs/superpowers/specs/`、`docs/superpowers/plans/` 是版控裡的實體文件
* `AGENT_START_HERE.md` 的必讀清單第 4 項直接點名該 spec;`00_Constitution/core.md`
  也把它列為權威設計

也就是說,那裡讓 superpowers「有感」的方式,是**專案自己的入口文件在每個 session 開頭把人推進去**,
而不是等模型從技能描述裡自己挑。

本 repo 有一模一樣的 `docs/superpowers/` 目錄,**但沒有任何東西把 session 導向它**。

## 結論與可做的事(未決定,待擁有者選)

1. **點名才有效,那就點名。** 把 superpowers 三個最有感的技能接進既有的形狀路由:
   bug → `systematic-debugging`、實作 → `test-driven-development`、
   宣稱完成前 → `verification-before-completion`。
   這是**目前唯一有實測效果的機制**(路由點名的四個技能是唯一跨 session 被打開的)
2. **把從未被打開的降級。** 44% 的提示預算換 0 次使用。降到目錄層(僅名稱)可回收大部分
3. **蒸餾技能要嘛升上註冊層並被點名,要嘛承認它們是文件而不是執行期能力** ——
   現在這個狀態是兩頭落空

**先量再改**:三者都可以先做 1,量一次真實使用,再決定 2 與 3。
