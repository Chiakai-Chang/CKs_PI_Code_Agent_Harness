# PM Skills Bridge Context

This extension bridges the **PM Skills Marketplace (phuryn/pm-skills)** into the Pi Harness using **Library Mode**.

## Core Mandate: On-Demand Wisdom
To maintain the lightweight advantage of Pi, you MUST NOT load all PM skills simultaneously. Instead, act as a **Librarian**:
1.  **Direct Commands**: Use the "Golden 5" commands for immediate common tasks:
    *   `/pm:prd-audit`: Use before implementation to ensure the spec is complete.
    *   `/pm:north-star`: Use to align business goals.
    *   `/pm:interview`: Use to distill user feedback.
    *   `/pm:assumption`: Use to de-risk high-stakes features.
    *   `/pm:roadmap`: Use for strategic planning.
2.  **Dispatcher Protocol**: If the task is specialized (e.g., "Pricing Strategy" or "PESTLE Analysis"), activate the `pm-dispatcher` skill to locate and inject only the relevant framework from `external/pm-skills/`.

## Quality Standard: encoded Frameworks
When using these skills, ensure the output adheres to the specific frameworks of Marty Cagan, Teresa Torres, etc., as defined in the source files. Do not default to generic AI prose.

## Persona Alignment
PM skills are primary tools for the `pm-expert` and `omc-pm` agents. `coder` agents should only use `/pm:prd-audit` to verify their own understanding of requirements.

---
**本文件由 pm-skills-bridge 提供，確保 100+ 個頂尖 PM 框架以「零負擔」方式賦予 Pi 助手產品合夥人的智慧。**
