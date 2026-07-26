---
name: grilling-protocol
description: Product clarification and evidence verification standard for Pi Coding Agent Harness — One-question-at-a-time interview, ambiguity resolution, architectural trade-off evaluation, edge case coverage, and immutable evidence verification.
---

# Grilling & Evidence Verification Protocol

This skill establishes the **Grilling Protocol** and **Evidence-Based Quality Gate Standard** for `CKs_PI_Code_Agent_Harness`.

---

## 1. Core Principles of Grilling

Before locking any plan, spec, or complex feature implementation, the agent MUST grill the user to resolve all product ambiguities:

1. **One Question at a Time**: Never dump multiple complex questions on the user at once.
2. **Include Recommendations**: For every question asked, provide a well-reasoned recommended answer based on repository inspection.
3. **Inspect First**: Check existing code, tests, and documentation before asking questions the codebase can already answer.

---

## 2. Mandatory Coverage Areas

Every grilling interview MUST cover these 3 critical categories:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Grilling Coverage Triad                         │
├──────────────────────┬────────────────────────┬────────────────────────┤
│ 1. Ambiguity         │ 2. Architecture        │ 3. Edge Cases          │
│ • Requirements with  │ • Tech stack choices,  │ • Empty/invalid input, │
│   multiple possible  │   persistence, data    │   auth timeouts, network│
│   interpretations    │   boundaries & costs   │   failures & limits    │
└──────────────────────┴────────────────────────┴────────────────────────┘
```

---

## 3. Immutable Evidence Artifacts (QA Gate)

"Done" is defined as **verified evidence**, not an empty task list or chat quietness.

- Every completed task MUST produce empirical execution proof (test run logs, CLI output, artifact diffs).
- Evidence logs MUST be checked for non-zero exit codes.
- Silently ignoring failed assertions or substituting mock pass responses is strictly forbidden.

---

## 4. Verification Checklist

- [ ] Has the grilling interview resolved ambiguous requirements, trade-offs, and edge cases?
- [ ] Have acceptance checks been defined for each decision?
- [ ] Has empirical evidence (unit test output or build logs) been captured?
- [ ] Does `python scripts/validate-config.py` pass with 0 errors?
