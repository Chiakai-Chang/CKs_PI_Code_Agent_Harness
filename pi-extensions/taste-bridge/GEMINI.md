# Taste Engine Bridge Context

This extension bridges the **Taste-Skill (Premium UI/UX Engineering)** framework into the Pi Harness.

## Core Mandate: Eliminating Generic Slop
When creating or modifying frontend code (React, Next.js, Tailwind), you MUST adhere to the following **Anti-Slop Directives**:
1.  **Metric-Based Control**: Default to the Premium Baseline:
    - `DESIGN_VARIANCE`: 8 (Favor asymmetric, overlapping, and left-aligned layouts).
    - `MOTION_INTENSITY`: 6 (Favor Spring Physics and perpetual micro-interactions).
    - `VISUAL_DENSITY`: 4 (Favor generous whitespace and "Art Gallery" breathing room).
2.  **Strict Bias Correction**:
    - **No Pure Black**: Use `Zinc-950` or `Off-Black`.
    - **No AI Purple**: Avoid generic neon gradients and purple glows.
    - **No Inter Font**: Favor `Geist`, `Outfit`, or `Satoshi` for premium feels.
    - **No Card Overuse**: Use space and borders for grouping unless elevation is required.

## Technical Standards
*   **Viewport Stability**: Always use `min-h-[100dvh]` instead of `h-screen`.
*   **Performance**: Animate only via `transform` and `opacity`. Isolate CPU-heavy animations in microscopic Client Components.
*   **Dependency Guard**: Always verify `package.json` before importing 3rd party libraries like `framer-motion`.

## Workflow Orchestration
*   Use `taste-design` for all new UI feature implementation.
*   Use `taste-redesign` when auditing or upgrading existing project aesthetics.
*   The "Three Dials" should be dynamically adjusted based on user feedback (e.g., "Make it more information-dense" -> increase `VISUAL_DENSITY`).

---
**本文件由 taste-bridge 提供，確保「專家級審美」與「頂級性能」在 Pi Harness 中成為預設標準。**
