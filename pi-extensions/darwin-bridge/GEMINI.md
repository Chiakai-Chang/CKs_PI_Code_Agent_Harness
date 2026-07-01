# Darwin Bridge

This extension bridges [alchaincyf/darwin-skill](https://github.com/alchaincyf/darwin-skill) into the Pi Harness.

## Available Actions
*   `/darwin:score`: Score any target `SKILL.md` using the 9-dimensional SkillLens rubric.
*   `/darwin:optimize`: Run the autonomous evolutionary hill-climbing optimization loop on a skill document.

## 9-Dimension Rubric Overview
1.  **Frontmatter Quality** (7%)
2.  **Workflow Clarity** (12%)
3.  **Failure Mode Coding** (12%) — Must explicitly code fallback/error paths.
4.  **Checkpoint Design** (6%) — Must include explicit confirmation points.
5.  **Actionable Specificity** (17%) — No soft words like "suggested" or "depends on".
6.  **Resource Integration** (4%)
7.  **Overall Architecture** (12%) — No AI slop words.
8.  **Execution Performance** (23%) — Sandbox test run evaluation.
9.  **Risk-Action Blacklist** (6%) — Must include "what NOT to do".
