---
name: research-task-routing
description: Use when a request asks for research, a market survey, competitive analysis, a landscape review, a feasibility study, a technology comparison, an audit, or any brief naming several things to find out — 市場調查、競品分析、可行性研究、技術比較、盤點、產業研究. Also use when one request contains several separate deliverables. Routes the work to brainstorming and planning-with-files before any searching starts, so a multi-part brief does not become one round of web searches and a summary.
---

# research-task-routing

This skill exists because of a measured gap, not a preference.

`scripts/measure-triggers.py`, local model, isolated sessions, neutral cwd, three repeats:

```
debug-methodology         2/3   67%
multi-step-methodology    0/3    0%
```

A debugging request fires the methodology because it lands in
`systematic-debugging`'s vocabulary. A market survey lands in nobody's:
`brainstorming` describes itself as being for *creating features, building
components*, and `planning-with-files` for a *complex multi-step task*. Those
skills are in submodules and their descriptions are not ours to change. This one
carries the vocabulary they are missing.

## When this fires

A brief that names more than one thing to find out. Three shapes cover most of it:

* **Research / survey** — "market survey of X: competitors, pricing, gaps"
* **Comparison** — "compare A and B on licensing, price, self-hosting"
* **Audit / inventory** — "go through the codebase and list every place that does X, why, and what it costs"

## What to do

**1. Settle scope before searching.**
If any deliverable is ambiguous — what counts as a competitor, which market, how
recent — load `brainstorming` and resolve it with the user first. Searching an
unclear brief produces an answer to a question nobody asked.

**2. Write the plan down.**
Load `planning-with-files` and write `task_plan.md` with **one phase per
deliverable**. The plan is what makes this recoverable when context is compacted;
a plan held in conversation is lost at the first compaction.

**3. One phase at a time.**
Finish and verify a phase before starting the next. A single round of fifteen
searches produces a summary that cannot be checked, because there is no record of
which finding came from where.

**4. Cite where each finding came from.**
A research deliverable with no sources is not a deliverable. Name the page for
each claim as you go, not at the end from memory.

## When NOT to use this

A single lookup. "What is the latest version of Zig" is one question with one
answer, and routing it through a planning phase costs minutes and buys nothing.
If a brief only looks long because it is politely worded, treat it as the single
thing it is.

## Why the plan is a file

Findings that live only in conversation are gone at the next compaction, and a
long research task will hit one. `task_plan.md` and `findings.md` survive it —
that is the whole reason `planning-with-files` exists.
