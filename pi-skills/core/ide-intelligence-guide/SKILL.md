---
name: ide-intelligence-guide
description: IDE-wired intelligence & model-adapted edit standard for Pi Coding Agent Harness — Model-tuned diff formats, LSP diagnostics verification, and tiered model role routing.
---

# IDE Intelligence & Model Adaptation Standard

This skill establishes the **IDE-Wired Code Intelligence Standard** distilled from Oh My Pi (`oh-my-pi`).

---

## 1. Model-Adapted Edit Formats

Different LLMs excel with different edit representations:
- **Fast / Compact Models**: Prefer exact line-replacement blocks (`TargetContent` -> `ReplacementContent`) to prevent diff parsing loops.
- **Large Reasoning Models**: Prefer unified diff context snippets with explicit line range bounds.

Agents MUST adapt their edit strategy to the target model's strengths to avoid token retry cascades.

---

## 2. LSP Diagnostics Before Edit Finalization

Before asserting that code changes are correct:
1. Inspect syntax/type diagnostics via language tools or static check commands.
2. Verify import statements exist and parameter signatures match exact symbol definitions.
3. Fix language server diagnostics BEFORE claiming completion.

---

## 3. Sub-Model Tiered Routing

Task complexity determines model selection:
- **SMOL (Fast)**: Formatting, log viewing, simple single-line fixes, status reports.
- **BALANCED (Default)**: Normal feature development, refactoring, unit test creation.
- **MAX (Plan / Reasoning)**: Architecture planning, complex debugging, contrarian reviews.

---

## 4. Defense Checklist

- [ ] Has language/type diagnostic verification been performed on modified code?
- [ ] Are imports and parameter types explicitly verified against symbol definitions?
- [ ] Does `python scripts/validate-config.py` pass cleanly with 0 errors?
