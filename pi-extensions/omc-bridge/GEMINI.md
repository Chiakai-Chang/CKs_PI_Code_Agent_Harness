# OMC Agent Factory Bridge Context

This extension bridges the **oh-my-claudecode (OMC)** framework into the Pi Harness.

## Core Mandate: Multi-Agent Orchestration
When using OMC agents or skills, you MUST follow the **Team-First** philosophy:
1.  **Orchestration over Implementation**: As the main agent, your role is to coordinate specialized sub-agents (`omc-oracle`, `omc-ralph`, etc.) rather than doing everything yourself.
2.  **Verification-Driven Persistence**: Use `omc-sisyphus` logic for tasks that are error-prone. Never give up until a valid verification evidence is produced.
3.  **The HUD Spirit**: Provide transparent status updates about which sub-agent is active and what their current objective is.

## Strategic Agents
*   **omc-sisyphus**: Use for persistent debugging and long-running refactors.
*   **omc-oracle**: Use for high-level architectural review and decision-making.
*   **omc-ralph**: Use for resilient feature implementation with auto-recovery.

## Workflow Orchestration
*   Use `/omg:team` to initiate the phased pipeline: `Plan -> PRD -> Exec -> Verify`.
*   Maintain shared state under `.omg/state/` to ensure continuity across agent handoffs.
*   Tool mapping: Map OMC's CLI-first workers to Pi's `invoke_agent` mechanism.

---
**本文件由 omc-bridge 提供，確保多代理編排神力在 Pi Harness 中具備環境自適應能力。**
