---
name: research-task-routing
description: Use when a request asks for research, a market survey, competitive analysis, a landscape review, a feasibility study, a technology comparison, an audit, or any brief naming several things to find out — 市場調查、競品分析、可行性研究、技術比較、盤點、產業研究. Also use when one request contains several separate deliverables. Routes the work to brainstorming and pi-planning-with-files before any searching starts, so a multi-part brief does not become one round of web searches and a summary.
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
components*, and `pi-planning-with-files` for a *complex multi-step task*. Those
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
Load `pi-planning-with-files` and write `task_plan.md` with **one phase per
deliverable**. The plan is what makes this recoverable when context is compacted;
a plan held in conversation is lost at the first compaction.

**3. One phase at a time.**
Finish and verify a phase before starting the next. A single round of fifteen
searches produces a summary that cannot be checked, because there is no record of
which finding came from where.

**4. Record the URL with the finding, in this shape.**

Measured across five runs of one market-survey brief: four of them searched
10–20 times, opened 3–8 pages, wrote a `findings.md`, and recorded **zero URLs**.
The instruction to cite sources was already in this file and was not followed.
So it is a format now, where a blank column is visible:

```markdown
## Phase 1 — competitors

| Finding | Source |
| --- | --- |
| Ring, Eufy and Tapo hold the visible shelf space on momo | https://… |
| Local brand X sells only through Shopee | https://… |
```

Fill the Source cell **at the moment you read the page**, from the URL you just
opened. Reconstructing sources at the end, from memory, is how a report ends up
with none — that is the measured failure, not a hypothetical one.

A row with an empty Source is a finding you cannot defend. Either find the page
again or delete the row.

## When NOT to use this

A single lookup. "What is the latest version of Zig" is one question with one
answer, and routing it through a planning phase costs minutes and buys nothing.
If a brief only looks long because it is politely worded, treat it as the single
thing it is.

## Why the plan is a file

Findings that live only in conversation are gone at the next compaction, and a
long research task will hit one. `task_plan.md` and `findings.md` survive it —
that is the whole reason `pi-planning-with-files` exists.
