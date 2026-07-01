# Best Practices Bridge

This extension bridges [DenisSergeevitch/agents-best-practices](https://github.com/DenisSergeevitch/agents-best-practices) into the Pi Harness.

## Key Focus Areas
*   **Harness vs Model**: The LLM proposes actions, but the Harness governs authorization, security, and context logic.
*   **Context Compaction**: Ensure context is actively managed instead of dumped.
*   **Evals & Telemetry**: Enforce robust validation before production deployment.
