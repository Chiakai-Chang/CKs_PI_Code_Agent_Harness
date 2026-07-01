# Rationale: Distillation of ilang-ai/autocode

## 1. Why WO (Smart Refactor) Strategy?
Instead of mapping `ilang-ai/autocode` as a Git submodule, we opted for **Smart Refactor (Path 3)**.

*   **Syntax Mismatch**: AutoCode uses the specialized I-Lang protocol syntax (such as `::GENE`, `::PRIOR`, `::ACTIVATE`), which violates standard Markdown specifications. Parsing these directly inside Pi's standard markdown engines leads to parsing errors or logic hallucinations.
*   **Zero Dependencies**: By distilling the core behavior into `autocode-shipping/SKILL.md`, we inherit the core functional value (e.g., maximum 2-question clarification, Cloudflare/VPS deployment workflows, and minimal fix verification) without introducing any external environment requirements.

## 2. Core Value Added
*   **Decoupled Multi-Hop QA**: Enforces a strict 2-question limit to prevent AI-to-user question exhaustion.
*   **Deployment-Oriented Mindset**: Shifts the agent from "writing snippets" to "delivering production URLs" using edge environments (Cloudflare Workers).
