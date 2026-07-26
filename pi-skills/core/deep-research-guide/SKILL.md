---
name: deep-research-guide
description: Deep web research workflow with question decomposition, multi-agent fan-out web searching, gap assessment with hard ceiling limits, and cited Markdown report generation.
tools: read, grep, find, ls, bash
---

# Deep Research & Multi-Source Web Synthesis Guide (深度網頁研究與多源綜述指南)

This skill codifies the **Deep Research** methodology distilled from `pi-browser-harness`, enabling structured, multi-source web investigation with strict evidence attribution and strict iteration ceilings.

---

## 1. Core Workflow & Architectural Principles

### 1. Problem Decomposition (需求拆解)
- **Principle**: Complex research topics cannot be answered cleanly by a single query.
- **Rule**: Decompose the user's research request into **3–6 focused, mutually exclusive sub-questions** covering definitions, current state, competing solutions, technical trade-offs, and recent developments.
- **User Alignment**: State the exact sub-questions to the user before launching search subagents.

### 2. Isolated Multi-Agent Fan-Out (多代理隔離並行檢索)
- **Principle**: Executing raw web searches in the main agent context pollutes the prompt window with noisy HTML/JS clutter.
- **Rule**: Fan out **one `web-search-researcher` subagent per sub-question** in parallel. Subagents execute search via `web_search` / `web_open` or `camofox-stealth` in isolated tabs and return distilled, source-attributed findings (`[Title](URL)` + facts).

### 3. Coverage Assessment & Hard Ceiling Loop (覆蓋率評估與雙重硬門控)
- **Principle**: Autonomous research without stopping criteria risks infinite looping or budget exhaustion.
- **Hard Ceiling Limits**:
  - **Maximum Rounds**: At most **2 rounds** of research.
  - **Maximum Researchers**: At most **8 total subagent dispatches**.
- **WAF / Captcha Mitigation**: If a subagent encounters anti-bot captcha/WAF block (`invalid_state` / `reason: "captcha"`), surface it to the user immediately rather than entering retry loops.

### 4. Cited Markdown Report Generation (具名引用 Markdown 報告生成)
- **Principle**: Factual assertions must be empirically backed by source links.
- **Rule**: Synthesize all subagent findings into a structured Markdown document (e.g. `research-<topic-slug>.md` in the working directory).

---

## 2. Standard Report Structure (`research-<topic-slug>.md`)

```markdown
# {Research Title / Topic}

## Summary
{Synthesized executive overview across all sources.}

## {Sub-Topic / Sub-Question 1}
{Factual findings in prose. Every claim MUST carry an inline source link: e.g., ... as detailed in [Source Title](URL).}

## {Sub-Topic / Sub-Question 2}
...

## Unresolved Gaps & Open Questions
{Explicitly list any sub-questions cut off by the 2-round / 8-researcher hard ceiling or conflicting source claims.}

## Cited Sources
{Deduplicated list of all referenced URLs with full titles.}
```

---

## 3. Decision & Fallback Matrix

| Research Scenario | Recommended Action | Safeguard / Limit |
| :--- | :--- | :--- |
| **Broad / Ambiguous Topic** | Decompose into 3–6 sub-questions | Present sub-questions to user before search |
| **Standard Web Research** | Fan out subagents with `web_search` / `web_open` | 1 subagent per sub-question |
| **Anti-Bot / Captcha Wall** | Route subagent via `camofox-stealth` | Stop retry on captcha; notify user |
| **Gaps Remaining after Round 1**| Launch Round 2 targeting specific gaps | Hard ceiling: Max 2 rounds, max 8 subagents |
| **Final Output** | Write `research-<topic-slug>.md` & notify user | Every assertion must have inline `[Title](url)` |
