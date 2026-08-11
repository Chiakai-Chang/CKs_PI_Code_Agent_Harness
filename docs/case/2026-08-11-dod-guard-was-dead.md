# The DoD-artifact guard was dead on arrival (2026-08-11)

## What happened

Run 3 of the PiTaskLab T-A1 experiment reached `REVIEW` with an empty task
folder: no `output.md`, no `planning.md`, 1 of 11 DoD items met. The guard built
the day before — refuse the move into `REVIEW` when the recipe's Local DoD names
a file that does not exist — did not fire.

The session trace:

```
 18 write output.md content="## 多數值\n\ntimeout_ms 多數值:3000…
    !! C.A.S.E. 階段閘(CLAIM):這個佇列有 PENDING 任務,還沒有人認領。
 19 write status.txt content="IN_PROGRESS\n"
 20 write status.txt content="REVIEW\n"      <-- should have been refused
```

Call 18 carried the complete report. It was refused by a *different* guard (the
CLAIM phase gate), the model then claimed the task, and never wrote the report
again. Call 20 was the guard's whole reason to exist, and it was allowed.

## The defect

`missingDodArtifacts(taskDir, _cwd, existsSync)` sat inside `checkTransition()`.
`_cwd` is a parameter of `check()`, three call frames up — it does not exist in
that scope. Every REVIEW write therefore raised a `ReferenceError`.

The error never surfaced, because the call was wrapped in

```ts
try { missing = missingDodArtifacts(taskDir, cwd, existsSync); }
catch { missing = []; }        // unparsable recipe: not this guard's call
```

That `catch` was written for one failure mode (a recipe this guard cannot parse
must not stop the machine) and absorbed a fatal one of a different kind. Fail-open
on bad input became fail-open on broken code.

Fixing the identifier in `evaluate()` was not enough: `cwd` had to be threaded
through `evaluate()` **and** `checkTransition()`, which is two frames, and the
first fix silently left the second frame broken in exactly the same way.

## Why 1289 tests were green

Two test shapes, both worthless here:

1. The unit tests called `missingDodArtifacts` **directly**. The pure function
   was correct — it still is. It was never reached in production.
2. The wiring test asserted that the guard's **source text** contained
   `"missingDodArtifacts("`. It did contain it. Source text is not behaviour.

This is the fifth occurrence this week of an assertion satisfied by the shape of
the source rather than by what the code does.

A third shape nearly repeated the mistake: the replacement fixture used a task
folder named `Task_001`, which does not match `TASK_DIR_RE = /^Task_(\d+)_/`. On
that fixture `taskDirOf()` returned `null` and **every** status write was
allowed, including the literal string `bogus`. A test that fails for the wrong
reason is as uninformative as one that passes for the wrong reason; the tell was
that a deliberately invalid status was also allowed, which no live defect could
explain.

## What replaced it

`TestTheDodGuardBlocksInPractice` builds a real queue folder on disk and drives
`TaskQueueGuard.check()` — the same public entry point the bridge calls — with
the exact input of call 20. Four cases: artifact absent (refuse), artifact
present (allow), no `cwd` supplied (still refuse; the artifact lives in the task
folder), unparsable recipe (allow — the fail-open is intentional and stays).

Proven to fail against the defect by restoring `_cwd` and re-running: 2 failures,
both in the new class.

## The rule this leaves behind

**A guard is wired when its public entry point refuses; not when its helper
returns the right list, and not when the call appears in the file.** Every guard
in this repo should have at least one test that goes in through `check()` with a
tool name and an input object, on a fixture whose names satisfy the patterns the
production code matches on.

Related: `docs/case/2026-08-10-guards-collide.md` (call 18 is that document's
failure mode — one guard's refusal destroying another guard's evidence).

## 修好之後(run 4、run 5)

同一配置重跑兩次,兩次都 **11/11**。

`CLAIM_FIRST` 的新句子在 run 4 直接命中:call 15 帶著完成的報告被擋,模型認領之後
**在 call 19 重寫了報告**。run 3 在同一個位置沒有重寫,這是兩者唯一的行為差異。

驗收物守衛在兩個 run 裡都沒有開口 —— 因為沒有機會。**它仍然只有安裝版層級的證據**
(對 run 3 的那一次呼叫回 `BLOCKED`),沒有真實 session 的證據。依本 repo 的規矩,
這叫「機制在,live 生效待證」,不叫 working。

run 5 另外暴露一個誤擋:兩次只讀的

```
cd "D:/MyProject/PiTaskLab" && python3 -c "…glob.glob('data/*.json')…"
```

被 containment 判成寫入 `/*.json`。原因是路徑樣式的 `\/` 分支可以**從 token 中間**
開始比對,於是 `data/*.json` 被讀成 POSIX 絕對路徑。模型的反應不是放棄,而是繞路 ——
寫一個暫存腳本再執行,多花約十次呼叫(33 vs run 4 的 23)。已加 token 起始錨點,
並以「拿掉錨點只讓那三個新案例變紅」證明錨點是修正本身,而非順手改寫。

**守衛的誤擋不會讓工作停下,它讓工作變貴。** 這是一種比拒絕更難發現的成本 ——
最終 DoD 仍然 11/11,只有呼叫數會說話。
