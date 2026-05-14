# AIxBDD Bridge Context

This extension bridges the **Waterball AIxBDD** skills into the Pi Harness.

## Core Mandate: Behavior-Driven Integrity
When using AIxBDD skills, you MUST prioritize the **integrity of the BDD cycle**:
1.  **Fact-First (Discovery)**: Never plan until facts, activities, and rules are discovered and documented in Feature Specs.
2.  **Explicit Verification (RED)**: Before implementing any code, ensure you have a failing test that accurately captures the target behavior.
3.  **Faithful Reasoning (GREEN)**: Implement the minimal code necessary to pass the test.
4.  **Requirement Reconciliation**: When requirements change, use `/aibdd-reconcile` to ripple the changes through Discovery -> Plan -> Tasks -> Code.

## Workflow Orchestration
*   Use `/aibdd-kickoff` at the start of any BDD-driven feature.
*   Follow the pipeline: `Clarify -> Discovery -> Plan -> Tasks -> Implement`.
*   Maintain all artifacts in the `specs/` or feature-specific directory.

## Technical Alignment
*   AIxBDD skills are sourced from `external/aixbdd/.claude/skills/` via git submodule.
*   Ensure path resolution is correct relative to the project root.
*   Tool mapping: Use Pi's native tools (`read_file`, `replace`, `run_shell_command`) as defined in the skill instructions.

---
**本文件由 aixbdd-bridge 提供，確保 AIxBDD 流程在 Pi Harness 中具備環境自適應能力。**
