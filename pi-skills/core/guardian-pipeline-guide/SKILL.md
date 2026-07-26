---
name: guardian-pipeline-guide
description: Architectural standards for command guardians, structural workflow decomposition, and skill taxonomy classification.
tools: read, grep, find, ls, bash
---

# Guardian Pipeline & Workflow Architecture Guide (守護者管道與工作流架構指南)

This skill codifies the architectural principles derived from the agentic harness ecosystem, establishing **Guardian Pipelines**, **Workflow Decomposition**, and **Skill Taxonomy** standards for maximum harness resilience.

---

## 1. The Guardian Pipeline Contract (`detect` ➔ `parse` ➔ `review`)

Command guardians protect critical system state (Git commits, PRs, issues, destructive operations) by enforcing a 3-step pipeline:

```
[Command Invocation Event]
           │
     Step 1: DETECT (Fast regex match, no parsing overhead)
           │
     Step 2: PARSE (Extract AST / structured argument model)
           │
     Step 3: REVIEW (Present to user / evaluate safety gate)
           │
   ┌───────┼───────┐
 ALLOW   BLOCK  REWRITE
```

- **`detect`**: Fast boolean check determining if the command matches the guardian domain. Must return in <1ms without side effects.
- **`parse`**: Pure parser transforming string inputs into structured representations (e.g. flags, paths, target entities).
- **`review`**: Evaluates security policies and user confirmation gates. Returns `allow` (proceed), `block` (cancel with context message), or `rewrite` (sanitize command).

---

## 2. Workflow File Organization Standard

Complex multi-step workflows MUST decompose responsibilities into separate single-purpose modules:

- **`state.ts`**: Holds state interfaces, persistent storage schemas, and default state factories.
- **`lifecycle.ts`**: Handles activation, deactivation, workspace initialization, and session restoration.
- **`enforce.ts`**: Tool-call interception and execution gating rules.
- **`transitions.ts`**: Confirmation gates, step progression, and context injection.
- **`index.ts`**: Entry point and event bus listener registrations ONLY. Serves as a readable table of contents.

---

## 3. Skill Taxonomy Classification

All harness skills MUST adopt standardized domain-concern-suffix naming:

| Skill Suffix | Purpose & Scope | Example |
| :--- | :--- | :--- |
| **`*-guide`** | Step-by-step methodology and educational instructions | `planning-guide` |
| **`*-convention`** | Operational rules and boundary guidelines for tool usage | `git-commit-convention` |
| **`*-format`** | Structural templates and layout schemas for artifacts | `comment-format` |
| **`*-standard`** | Opinionated style, quality, and architecture benchmarks | `code-style-standard` |

---

## 4. Summary Checklist for Harness Extensions

1. Does every command gate implement `detect` $\rightarrow$ `parse` $\rightarrow$ `review`?
2. Are workflow concerns separated into `state`, `lifecycle`, `enforce`, `transitions`, `index`?
3. Are all skills properly suffixed with `-guide`, `-convention`, `-format`, or `-standard`?
