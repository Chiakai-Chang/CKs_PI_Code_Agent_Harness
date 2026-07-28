---
name: deep-research-guide
description: Deep web research using the deep_research tool, which runs each sub-question as its own isolated agent process and returns only the findings. Covers decomposition, when the fan-out is worth its wall-clock cost, and cited synthesis that never fills gaps from memory.
tools: read, grep, find, ls, bash
---

# Deep Research (深度網頁研究)

> **This is no longer a workflow you are asked to imagine performing.**
> The fan-out is a real tool — `deep_research`, registered by
> `pi-extensions/deep-research-bridge`. The previous version of this skill
> described decomposition, "fan out one `web-search-researcher` subagent per
> sub-question in parallel", and cited synthesis, while nothing in the harness
> implemented any of it. There was no subagent to dispatch.

---

## 1. What the tool actually does

`deep_research(question, subQuestions[])`

Each sub-question is spawned as its **own `pi --print` process** (Pi's documented
subagent pattern). That child has a fresh context, runs its own `web_search` /
`web_open`, and returns a short finding. Only the findings come back — **the
pages the child read never enter this conversation**.

That isolation is the whole point, and the reason is measured, not stylistic:

* `web_open` results on this machine ran to a median of 9,319 chars and a max of
  80,029 — roughly 20K tokens in one tool result.
* A 42,999-char tool result was observed making this exact local model lose the
  conversation mid-task.

So the win is **not** speed. It is that several pages of raw web content can be
read without any of it landing in your context.

---

## 2. When the fan-out is worth its cost

Sub-questions run **strictly one at a time**. The local llama.cpp server runs
with `-np 1`, so concurrent requests serialize — measured directly: two parallel
requests completed at 7.3s and 14.3s, not both at 7.3s. Each sub-question
therefore costs a full agent run of wall time.

**Use `deep_research` when** the question needs several genuinely different
things looked up **and** you do not want the raw pages in this context.

**Do not use it when:**
* One lookup answers it → call `web_search` / `web_open` directly.
* The sub-questions restate each other → you pay N runs for one answer.
* You already have the sources open → just read them.

The cap is **5 sub-questions**, and it is a hard limit, not a nudge.

---

## 3. Decomposition (yours, not the tool's)

Pass sub-questions that are:

* **Separately answerable** — each researchable without the others' answers.
* **Concrete** — "what does the vendor's pricing page list for tier 2" beats
  "investigate pricing".
* **Non-overlapping** — overlap means paying twice for one finding.

State the sub-questions to the user *before* calling the tool. On a local model
each one takes minutes; being told what is being researched, and getting a
chance to correct it, matters more here than it would on a fast model.

---

## 4. Synthesis (still yours)

The tool returns a digest with one section per sub-question.

1. **Keep the source URLs.** A finding without its URL is unverifiable and must
   be treated as unsupported.
2. **Where findings disagree, say so.** Do not average them into a false
   consensus and do not silently pick one.
3. **A failed sub-question stays unresolved.** The digest marks failures
   explicitly. Report the gap — never fill it from memory. Same rule as this
   repo's Evidence-Based Completion principle: absence of evidence gets
   reported, not papered over.
4. **Attribute per claim, not per report.** A trailing list of links does not
   tell the reader which claim came from where.

Write the result to `research-<topic-slug>.md` when the user wants a report:

```markdown
# {Topic}

## Summary
{Synthesis across sub-questions.}

## {Sub-question 1}
{Findings in prose. Every claim carries an inline link: ... as stated in [Title](URL).}

## Open questions
{Sub-questions that failed or returned nothing. Say so plainly.}
```

---

## 5. Slash command

`/deep-research <question>` starts the flow: decompose, call `deep_research`
once with the sub-questions, then synthesize a cited answer.

---

## 6. Failure modes

| Symptom | Meaning | What to do |
| :--- | :--- | :--- |
| "not available inside a research subagent" | You *are* a child process | Answer your own sub-question with `web_search` / `web_open` and report the finding |
| A section reads "failed after Ns" | That child errored or timed out | Report the gap; optionally retry that one sub-question alone |
| Every sub-question failed | Backend or model is down | Tell the user research could not run — do not invent findings |
| The digest looks thin | Sub-questions were too broad | Re-decompose into more concrete ones rather than re-running the same set |
| A page returns a bot wall | Anti-bot challenge, not content | Surface it; do not retry in a loop (`camofox-stealth` already spoofs fingerprints — a hard block usually means login is required) |
