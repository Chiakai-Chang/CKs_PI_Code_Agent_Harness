---
name: workflow-os-guide
description: Comprehensive guide for Workflow OS patterns in Pi Coding Agent Harness — Pins/Gates/Steers architecture, phase tool allowlisting, deterministic handoff generation, and orphan skill detection.
---

# Workflow OS Architectural Standard

This skill establishes the **Workflow OS Pattern** for autonomous agent execution within `CKs_PI_Code_Agent_Harness`.

---

## 1. Core Paradigm: Pins, Gates, and Steers

To prevent context bloat and prompt pollution, agents MUST NOT load all skills globally. Instead, follow the **Pins, Gates, Steers** pattern:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Workflow OS Architecture                        │
├──────────────────┬──────────────────────┬──────────────────────────────┤
│ 1. Pinned        │ 2. Gated             │ 3. Steered                   │
│ • Direct front-  │ • Phase tool         │ • Procedural text            │
│   matter skill   │   allowlists         │   prompts instructing        │
│   injection for  │ • RED test halts     │   on-demand loading of       │
│   slash commands │ • Commit validation  │   secondary skills           │
└──────────────────┴──────────────────────┴──────────────────────────────┘
```

### A. Pinned Skills
Explicitly load heavy specialized skills ONLY when the workflow reaches the point that needs them (e.g. starting new work -> `brainstorming`, beginning implementation -> `test-driven-development`). Name the skill; this harness installs no `/plan` or `/build` command to trigger one.

### B. Gated Execution
Enforce strict execution gates across phase boundaries:
- **PLAN Phase**: Allowed tools: file read/view, search. Disallowed: file edits, bash execution.
- **BUILD Phase**: Allowed tools: file edits, test execution. Disallowed: deployment, push.
- **REVIEW Phase**: Allowed tools: code audit, static inspection. Disallowed: core architecture modification without re-planning.
- **VERIFY/SHIP Phase**: Requires clean test exit codes (0) and verified git commit hash before claiming completion.

### C. Steered Transitions
Use clear procedural handoff triggers in prompt text to guide the agent to explicitly switch phases or load optional secondary skills.

---

## 2. Deterministic Handoff State Preservation (`HANDOFF.md`)

When context window compaction occurs or when suspending an active session:
1. Do NOT initiate expensive LLM calls to re-summarize context.
2. Extract state deterministically from the trajectory:
   - **Current Goal / Phase**
   - **Completed Verification Tests**
   - **Modified File List**
   - **Next Direct Action Steps**
3. Save structured state directly to `HANDOFF.md` or checkpoint artifact.

---

## 3. Orphan Skill Detection & Hygiene

A skill is defined as an **Orphan Skill** if:
- It is registered in `pi-skills/` but never referenced by any command, workflow guide, or managed script list.
- It contains empty placeholder hooks or unreferenced configuration templates.

All skills registered in `pi-skills/` MUST be explicitly declared in `scripts/restore.py` and `scripts/uninstall.py`.

---

## 4. Verification & Defense Checklist

Before completing any multi-phase workflow:
- [ ] Confirm all tests passed via actual CLI invocation (not assumptions).
- [ ] Verify `git status` shows zero untracked pollution in system workspace.
- [ ] Ensure configuration hygiene validation (`python scripts/validate-config.py`) returns 0 errors.
