# Evolution Engine Bridge Context

This extension bridges the **Evolver (Self-Evolution Engine)** framework into the Pi Harness using the **GEP (Genome Evolution Protocol)**.

## Core Mandate: Persistent Learning
When using evolution skills, you MUST prioritize the **long-term hardening of the Agent**:
1.  **Signal over Noise**: Use `/evolve:scan` to identify recurring failures. Do not treat random glitches as genetic defects.
2.  **Genetic Solidification**: After a successful `PIP` recovery or a major feature delivery, proactively ask the user: "Should I solidify this experience into a new Gene?"
3.  **Traceability**: Every evolution event must be logged in `events.jsonl` with clear rationale and signals.

## Operational Protocol
*   **The Gene Mapper**: You have direct read access to `external/evolver/assets/gep/genes.json`.
*   **Dynamic Adaptation**: Before complex tasks, check the Gene bank for relevant "Antibodies" (e.g., `gene_gep_repair_from_errors`).
*   **Collaboration with Reflect**: While `hello-reflect` updates `CLAUDE.md`, the Evolution Engine manages the structured strategy bank in `.omg/state/` or the GEP store.

---
**本文件由 evolution-bridge 提供，確保 AI 助手具備「持續進化、永不退化」的生命力。**
