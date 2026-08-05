# Measurements

Baselines produced by `scripts/measure-triggers.py --report`. Each line is one
run: date, scenario pass rates, and the notes from failing runs.

These exist so a prompt or routing change can be compared against what was there
before, rather than validated by a single manual run. Every prompt-shaping
decision in this harness was tuned blind until this file existed.

`trigger-baseline.jsonl` is append-only. Do not rewrite past entries — a baseline
that gets edited to match the current build is not a baseline.

## 判準演進（2026-08-05）

```
run1  activation 0/3   第一版路由：動作後投遞（tool_result）
run2  activation 3/3   第二版：動作前（before_agent_start）+ research-task-routing skill
run3  outcome    0/3   判準換成產出，但只讀聊天回覆 —— 量錯地方
run4  outcome    1/3   判準修正：答案 + 寫出的檔案
```

**run2 → run3 的落差是判準變嚴，不是退步。** activation 問「有沒有載入方法論」，
outcome 問「三個交付項有沒有涵蓋、有沒有至少兩個不重複來源」。前者 3/3 的那一版，
用後者量是 0/3——聊天回覆裡零個連結。

**run3 → run4 是修正我自己的量測錯誤。** 實測顯示模型引用了十個來源，寫在
`findings.md`——那正是 `planning-with-files` 規定 findings 該去的地方。只讀聊天回覆的
判準，恰好懲罰了正在被推動的那個行為。交付物是「答案 + 產出的檔案」。

## 目前的殘餘缺口（未解，如實記錄）

`multi-step-methodology` 產出判準 **1/3**。三次中兩次失敗，且都是 0 個來源。

其中一次（run2）讀了 7 次 SKILL.md，但讀的是 `~/.agents/skills/research/`——
**鄰居工具安裝的另一個 research skill**，不在本 harness 的 manifest 裡也不是 junction，
但 Pi 看得到（`.agents/skills/` 是跨工具通用位置）。它的 description 針對
「research a topic」寫得很直接，與 `research-task-routing` 搶同一類請求。

**不打算靠把描述寫得更強勢去搶。** 那是軍備競賽，且等於把使用率當目標。

## n=3 的解析度

本機模型 temperature 0.6。1/3 與 2/3 在三次取樣下分不開。要宣稱任何調整有效，
`--repeats` 需提高到 5 以上，否則量到的是雜訊。
