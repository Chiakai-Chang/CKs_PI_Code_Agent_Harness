# 既有技術登記表 (Prior-Art Register)

> **這份表由 `scripts/check-prior-art.py` 強制**(在 CI 裡)。
> 它不是清單,是**動工前的必查項**:每一個外部來源都必須有一列,每一個落在磁碟上的
> clone 都必須被宣告,每一份宣稱存在的收穫文件都必須真的存在。

## 為什麼有這份表

2026-08-06,一整天用來重建兩個 `reference/pi-until-done` 已經實作好的機制:
以 `agent_settled` 驅動的續跑迴圈,以及一個以證據裁決完成聲明的 judge。

而我們**自己寫的筆記**
[`docs/superpowers/pi-until-done-learnings/02-bounded-execution-and-spin-detection.md`](../superpowers/pi-until-done-learnings/02-bounded-execution-and-spin-detection.md)
第 39 行白紙黑字寫著 `agent_settled` owns automatic continuation,
第 12–16 行連狀態機都抄下來了(含 `progressSignalsThisTurn === 0 → spin guard`)。

推進器做在 `turn_end`,退場計數器數注入次數。五次真實 run、兩小時,
「實測發現」的兩個缺陷就是那兩行。**文件在,只是沒有東西把它接到工作上。**

**clone 回來 ≠ 審視過;審視過 ≠ 記得住。** 這一列一列的「審視狀態」欄,就是這句話的執行版。

## 怎麼用

* **設計任何新機制之前**:在這張表裡找同類能力,逐項寫「採用 / 移植 / 不做 + 理由」,
  寫進該任務的 `recipe.md > Input Sources`。
* **審視完一個來源**:把狀態改成 `已審視`、填收穫文件路徑與日期,
  並在「明確不採用」欄寫下**為什麼不用** —— 那一欄比「已採用」更重要,
  因為沒寫下來的否決會被下一個人重做一次。
* **狀態語彙**:`已審視`(讀過實作、有收穫文件)/ `未審視`(clone 了,沒有實作層紀錄)。

---

## 登記表

| 來源 | 類型 | 位置 | 審視狀態 | 收穫文件 | 已採用 | 明確不採用 | 最後審視 |
|---|---|---|---|---|---|---|---|
| pi-until-done | reference-clone(**README 未列**) | reference/pi-until-done | 已審視(實作層) | docs/superpowers/pi-until-done-learnings/ · docs/prior-art/2026-08-06-pi-until-done-loop-reference.md | compaction 生存套件、Verifiability Block、hook 紀律文件;**待移植**:`agent_settled` 續跑、加權 progress signal、自動化失敗不動任務狀態、終端步驟不計時 | turn budget 對話框、YAML/widget UI、mise 綁定;**原本排除的 judge / Ralph loop 已被 Task_010/011/001 的工作事實推翻,重新列為待決** | 2026-08-06 |
| oh-my-pi | reference-clone | reference/oh-my-pi | 已審視 | docs/superpowers/oh-my-pi-learnings/ | hashline edit 概念、context discovery 觀念 | 整套 natives/bash runtime | 2026-08-06 |
| camofox-browser | reference-clone | reference/camofox-browser | 已審視 | docs/core/ | `stealth-web-bridge` 的 `web_search`/`web_open` | — | 2026-07-12 |
| prime-agent | research-clone(**pi-mono 的 fork,非 Pi 擴充**) | research/prime-agent | 已審視(實作層) | docs/prior-art/2026-08-08-prime-agent-review.md | **待移植**:supplemental-only 提示層(base 不可改,有真實拒絕)、refinement 事件 append-only + rollback、local/global 分域且預設 local | 整套 RLM/IPython runtime、換底座(它釘 pi-coding-agent ^0.7.1,我們跑 0.83)、**「evidence-backed」的自陳式證據**(`evidence: proposal.rationale`,未驗證) | 2026-08-08 |
| market-research | reference-clone | reference/market-research | 未審視 | — | — | — | — |
| pi-browser-harness | reference-clone | research/pi-browser-harness | 已審視(實作層) | docs/prior-art/2026-08-09-cited-but-unreviewed.md | `inBoilerplate` 子樹過濾概念 → `stealth-web-bridge/readability.ts`;截斷策略 → `truncate.ts`；蒸餾為 `deep-research-guide`、`browser-automation-guide`(**僅散文,無實作層紀錄**) | 以文字/連結密度猜測正文的啟發式 —— 我們有無障礙樹的語意角色,按角色過濾更可靠且不需注入腳本 | 2026-08-09 |
| metaharness | reference-clone | research/metaharness | 已審視(實作層) | docs/prior-art/2026-08-09-metaharness-review.md | **待移植**:量測噪音底線再解讀差異(ADR-138 的 `n ≳ (sd/(Δ/2))²`);ADR 狀態詞彙區分 `Accepted` 與 `Accepted (measured)`；蒸餾為 `harness-factory-guide`(同上) | Darwin Mode 整套演化機制(規模與目的不同)、223 個 ADR 的文件密度、三環測試分層(已有等價物)。**另更正**:我先前引用其 ADR-010 當根據時,未察覺其狀態是 `Proposed` 而非 `Accepted` | 2026-08-09 |
| harness-engineering | reference-clone | research/harness-engineering | 已審視(實作層) | docs/prior-art/2026-08-09-harness-engineering-review.md | **已採用**:ADR-0001「專案目標才是完成權威」→ 當場抓到 `global_dod.md` 是無人讀取的未填樣板,已改寫;**待移植**:ADR-0014 證據產物不可變(create-only、覆寫即失敗、以 digest 引用),與 prime-agent 的 refinement journal 同族一起設計 | plugin marketplace / 多 host 路由(我們單一 host 單一模型)、`roles.json` 階段路由、Supervisor/lease/fence/beacon 車隊治理層(我們一次跑一個 run,且剛被孤兒行程教訓過)、背景 worker 常駐。**記下觸發條件**:ADR-0018 的 fail-closed + 持久請求,若出現「因缺能力而反覆產出不可驗證結論」再移植 | 2026-08-09 |
| the-last-harness | reference-clone | research/the-last-harness | 已審視(實作層) | docs/prior-art/2026-08-09-the-last-harness-review.md | **待移植**:旗標在 `session_start` 快照而非即時讀取(直接提升量測可複驗性);**待評估**:子代理與動作的封閉允許清單(`contrarian`/`oracle` 由政策指派,而非放在 catalog 等模型想到);**長期標準**:「使用者忘了觸發某事」= harness 的失敗 | 整套 architect 自動接手編排(假設多個可靠子代理 + 充足 token;我們是單一本機模型)、使用者自訂 embedded subagents(內建角色都還沒有)、`/experimental` 指令族(旗標只有一個半,做 UX 是為不存在的規模建設施) | 2026-08-09 |
| ultimate-pi | reference-clone | research/ultimate-pi | 未審視 | — | 蒸餾為 `adversary-review`(同上) | — | — |
| pi-autoresearch-harness | reference-clone | research/pi-autoresearch-harness | 未審視 | — | 蒸餾為 `autonomous-experiment-guide`(同上) | — | — |
| pi-tool-repair-layer | reference-clone | research/pi-tool-repair-layer | 已審視(實作層) | docs/prior-art/2026-08-09-cited-but-unreviewed.md | **目前不採用**;mutation-score 的**分層**概念已用於 `check-guard-mutations`(百分比不採用)；蒸餾為 `tool-repair-guide`(同上) | 整套 tool-call 修復層 —— **我們沒有量到這個問題**(實測 35/35 正確 tool call)。**觸發條件**:若日後量到畸形 tool call,這是移植來源。其 `testing-strategy.md` 是 AI 生成、mutation 欄位全是目標值而非實測 | 2026-08-09 |
| agentic-harness.pi | reference-clone | research/agentic-harness.pi | 未審視 | — | 蒸餾為 `guardian-pipeline-guide`(同上) | — | — |
| pi-superagents | reference-clone | research/pi-superagents | 未審視 | — | 蒸餾為 `subagent-orchestration-guide`(同上) | — | — |
| Huiyu-Pi | reference-clone | research/Huiyu-Pi | 未審視 | — | 蒸餾為 `minimal-prompt-guide`(同上) | — | — |
| auto-pi | reference-clone | research/auto-pi | 已審視 | docs/prior-art/RATIONALE.md | **階段工具白名單(`tool_call` 擋)**、操作綁技能、RED guard、純邏輯與 runtime 分離 | install.sh/mise/jq 依賴、六個預設 workflow 與 palette、1557 行單檔形狀、全自主模式 | 2026-08-06 |
| oh-my-pi-audreyt | reference-clone | research/oh-my-pi-audreyt | 未審視 | — | 蒸餾為 `ide-intelligence-guide`(同上) | — | — |
| oh-my-pi-can1357 | reference-clone | research/oh-my-pi-can1357 | 未審視 | — | 同上 | — | — |
| claude-reflect | distillation-source | (無 clone) | 已審視 | docs/core/ | 本地移植為 `hello-reflect` | — | 2026-07-07 |
| ecc | submodule | external/ecc | 已審視 | README.md 的 `eccSkillModules` 段 | 依 module 精選 65 技能(全量 277 個 = 27.5k tokens) | 全量註冊 | 2026-07-28 |
| planning-with-files | submodule | external/planning-with-files | 已審視 | pi-extensions/planning-with-files-bridge/ | Verifiability Block 注入 | — | 2026-08-06 |
| superpowers | submodule | external/superpowers | 已審視 | docs/superpowers/ | brainstorming / TDD / writing-plans 流程技能 | — | 2026-08-06 |
| Local-Agent-Workspace | submodule | external/Local-Agent-Workspace | 已審視 | docs/case/ | C.A.S.E. 協定 + `verify.py` 強化(已回貢上游) | — | 2026-08-06 |
| mece-autopilot | submodule | external/mece-autopilot | 已審視 | docs/mece/rounds/ | 多角色辯論 + SWOT/TOWS 收斂 | — | 2026-08-06 |
| yes.md | submodule | external/yes.md | 已審視 | pi-extensions/yes-hooks-bridge/ | pre-bash-guard 硬擋毀滅性指令 | — | 2026-07-12 |
| llm-wiki-plugin | submodule | external/llm-wiki-plugin | 未審視 | — | 以 skill 形式註冊 | — | — |
| prompt-master | submodule | external/prompt-master | 未審視 | — | 以 skill 形式註冊 | — | — |
| caveman | submodule | external/caveman | 未審視 | — | 以 skill 形式註冊 | — | — |
| andrej-karpathy-skills / karpathy-skills | submodule | external/karpathy-skills | 未審視 | — | 以 skill 形式註冊 | — | — |
| taste-skill | submodule | external/taste-skill | 未審視 | — | `enableTasteBridge` 預設關閉 | — | — |
| evolver | submodule | external/evolver | 未審視 | — | 以 skill 形式註冊 | — | — |
| darwin-skill | submodule | external/darwin-skill | 未審視 | — | bridge 註冊 | — | — |
| qiushi-skill | submodule | external/qiushi-skill | 未審視 | — | bridge 註冊 | — | — |
| agents-best-practices | submodule | external/agents-best-practices | 未審視 | — | bridge 註冊 | — | — |
| graphify | submodule | external/graphify | 未審視 | — | bridge 註冊 | — | — |
| loopy | submodule | external/loopy | 已審視 | docs/prior-art/RATIONALE.md | 「迴圈必須有終端狀態」的定義;「弱檢查」作為可審計類別 | Loop Library 網站與發佈流程、discover/craft 互動(與 MECE-Autopilot 重疊) | 2026-08-06 |
| OmniHeal | reference-clone(擁有者自有專案) | research/OmniHeal | 已審視 | docs/prior-art/RATIONALE.md | **本登記表與 RATIONALE 格式即取自它**;Task Queue 恢復點定義;3-Strike 的「換一種方式」分層 | 零安裝硬約束、三個健檢技能、SWOT 產出格式、Phase 掃描模型(領域不同) | 2026-08-06 |

---

## 名單漂移:三份清單本來就對不起來

本表的第一版是照 `external-manifest.json` 建的,那是錯的起點 ——
**README 才是擁有者實際讀到、記得的清單**。把三份對起來之後:

| 漂移 | 內容 | 意義 |
|---|---|---|
| README 有、manifest 無 | `camofox-browser` | 隱身瀏覽引擎,實際有用,卻不在來源宣告裡 |
| manifest 有、**README 無** | **`pi-until-done`** | **有答案的那個 repo,不在擁有者會讀到的清單上** |
| 名稱不一致 | README 寫 `andrej-karpathy-skills`,本地叫 `karpathy-skills` | 兩份清單互查時會漏掉 |
| 磁碟有、兩份都無 | `market-research`、`OmniHeal` | 沒有人決定要留,但一直在。`taiwan-smart-doorbell` 查證後是**空目錄**,已刪除 |

`scripts/check-prior-art.py` 現在同時比對 **README 連結 / manifest 宣告 / 磁碟 clone**,
任何一邊有而登記表沒有就紅。上面四項就是它第一次跑出來的東西。

## 已知的兩個結構性問題(不是清單,是要修的東西)

**一、「蒸餾」沒有留下勘查紀錄。** 13 個 research clone 蒸餾成了 13 個技能,
但技能檔本身**不寫來源**(`grilling-protocol/SKILL.md` 通篇沒有 `harness-engineering`),
而且 9 個來源在 `docs/` 與 `pi-skills/` 裡出現 **0 次**。
所以「看過什麼、為什麼只取這些、放棄了什麼」全部遺失 —— 下一個人只能重看一遍。

**二、磁碟 11 GB,且集中在四個。** `oh-my-pi-can1357` 3.3G、`oh-my-pi-audreyt` 3.0G、
`metaharness` 1.9G、`ultimate-pi` 1.1G。全部是 reference-only,
不需要完整歷史 —— `--depth 1` 重新 clone 可回收約 8 GB。
(`research/` 與 `reference/` 都已在 `.gitignore`,**不會污染 repo**,這一點沒有問題。)
