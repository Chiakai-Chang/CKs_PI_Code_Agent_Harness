---
name: subagent-orchestration-guide
description: Architectural standards for subagent role specialization, model tiering (cheap/balanced/max), lineage-only context pruning, and trust-gated execution.
tools: read, grep, find, ls, bash
---

# Subagent Orchestration & Model Tiering Guide (子代理調度與模型分層指南)

This skill codifies the architectural rules for **Role-Specific Subagent Delegation**, **Abstract Model Tiering**, and **Lineage-Only Context Pruning** within the harness.

---

## 1. Abstract Model Tiering Architecture

To balance cost, speed, and reasoning depth, delegate tasks to subagents using abstract **Model Tiers** instead of hardcoded model strings:

| Model Tier | Ideal Workloads | Typical Models | Recommended Thinking Level |
| :--- | :--- | :--- | :--- |
| **`cheap`** | Fast file scanning, repo scouting, lint/formatting, simple diff summaries | Flash / Haiku / Mini models | `off` or `low` |
| **`balanced`** | Single-file feature implementation, unit test writing, standard bug fixes | Sonnet / GPT-4o / Pro models | `medium` |
| **`max`** | Architecture design, multi-file refactoring, security reviews, contrarian audits | Opus / O1 / High-Reasoning | `high` |

---

## 2. Lineage-Only Context Pruning Rule

- **Problem**: Passing full parent conversation history to subagents wastes up to 60%+ input tokens and introduces irrelevant context noise.
- **Rule**: Subagents MUST default to **`lineage-only`** context mode.
- **Implementation**: Supply a clean, self-contained **Work Brief** containing:
  1. Exact task description & acceptance criteria.
  2. Targeted file paths and relevant code snippets.
  3. Non-goals and specific constraints.

---

## 3. Project Trust & Privilege Protection

- **Rule**: Subagent processes MUST mirror the parent process's Project Trust boundary.
- **Behavior**:
  - When parent context is **TRUSTED**: Subagents inherit `--approve` flags.
  - When parent context is **UNTRUSTED**: Subagents MUST receive `--no-approve` flags, preventing silent escalation of file writing or command execution privileges.

---

## 4. Subagent Frontmatter Specification

Role-specific subagent definitions MUST declare explicit frontmatter properties:

```yaml
---
name: role-name
description: Purpose of this subagent.
modelTier: cheap | balanced | max
thinking: off | low | medium | high
tools: read, grep, find, ls
inheritSkills: false
skills:
  - targeted-skill-name
---
```
