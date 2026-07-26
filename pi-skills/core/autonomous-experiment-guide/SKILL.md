---
name: autonomous-experiment-guide
description: Guidelines for autonomous experiment loops, statistical confidence evaluation (MAD), backpressure validation, and worktree isolation.
tools: read, grep, find, ls, bash
---

# Autonomous Experiment & Quantitative Optimization Guide (自主實驗與定量優化指南)

This skill codifies the rules for conducting **autonomous experiment loops** within the harness, combining **Git Worktree Isolation**, **MAD-based Statistical Confidence Scoring**, and **Backpressure Safety Checks**.

---

## 1. Core Principles

### 1. Worktree Isolation First
- **Rule**: Never run experimental mutation loops directly on the primary working directory or active Git branch.
- **Action**: Always spawn an isolated git worktree at `autoresearch/<session-id>/` before starting an iteration loop. All trial commits remain isolated until explicitly merged or cleared.

### 2. Quantitative Metric & Noise Elimination (MAD Confidence)
- **Problem**: Metric jitter (e.g. CPU load spikes, network latency variance) can cause false-positive "improvements".
- **Rule**: Calculate Median Absolute Deviation (MAD) over historical metric runs. Define `Confidence = |Best_Improvement| / MAD`:
  - $\ge 2.0\times$: Confirmed real improvement.
  - $1.0\sim 2.0\times$: Marginal improvement; re-verify.
  - $< 1.0\times$: Noise level; do NOT claim success without multiple confirmatory runs.

### 3. Backpressure Correctness Checks (`checks.sh`)
- **Rule**: Quantitative speedups/reductions must NEVER compromise system correctness.
- **Action**: Every successful benchmark MUST be followed by a backpressure check (unit tests, typechecks, linter). If backpressure fails, the run is logged as `checks_failed` and immediately reverted regardless of metric gains.

### 4. Target Threshold & Budget Guardrails
- **Rule**: Autonomous loops must set explicit stopping criteria (`target_value` or `max_experiments`) to prevent runaway API token consumption.

---

## 2. Standard Experiment Workflow

```
[Start Experiment] ──► Create Git Worktree ──► Establish Baseline
                                                     │
┌────────────────────────────────────────────────────┘
▼
[Propose Hypothesis & Edit] ──► Run Benchmark (Metric N)
                                       │
                        Did Benchmark Pass & Metric Improve?
                                       │
                       ┌───────────────┴───────────────┐
                      YES                             NO
                       │                               │
            Run Backpressure Checks           Revert & Log Discard
                       │
              Did Checks Pass?
                       │
       ┌───────────────┴───────────────┐
      YES                             NO
       │                               │
Commit & Log Keep              Revert & Log Checks_Failed
       │
Target / Max Reached? ──► YES ──► Merge or Clean Worktree
       │
      NO
       │
       └───► Loop Back to Edit
```
