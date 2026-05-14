# Addy Osmani Agent Skills Bridge Context

This extension bridges **Addy Osmani's Agent Skills** into the Pi Harness.

## Core Mandate: Quality Gates & Discipline
When using these skills, you MUST enforce the **Quality Gates** defined in the `SKILL.md` files:
1.  **Anti-Rationalization**: Do not accept common AI excuses for skipping tests or specs. Refer to the "Anti-rationalization Table" in any active skill.
2.  **Explicit Verification**: Every task must end with a `Verification` section containing concrete evidence (e.g., build logs, test results).
3.  **Process Over Prose**: Follow the structured steps exactly. Do not replace rigorous engineering with conversational summaries.

## High-Value Skills
*   **/performance**: Use for critical web performance auditing.
*   **/addy:code-simplify**: Use for refactoring complex, technical-debt-heavy code.
*   **Security & Hardening**: Use when handling sensitive data or public-facing endpoints.
*   **Doubt-Driven Development**: Use when requirements are fuzzy or assumptions are high-risk.

## Technical Alignment
*   Skills are sourced from `external/addyosmani-skills/skills/`.
*   Commands are mapped with an `addy:` prefix to avoid collision with existing Harness commands.
*   The bridge ensures that Addy's "Google-grade" standards are available as a global constraint for the Pi Assistant.

---
**本文件由 addyosmani-bridge 提供，確保工業級開發標準在 Pi Harness 中具備環境自適應能力。**
