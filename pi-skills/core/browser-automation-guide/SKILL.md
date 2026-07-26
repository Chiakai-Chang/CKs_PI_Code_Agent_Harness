---
name: browser-automation-guide
description: Best practices for browser automation, AX-Tree ref-first targeting, framework-safe input writes, and stealth fallback strategy.
tools: read, grep, find, ls, bash
---

# Browser Automation & Stealth Integration Guide (瀏覽器自動化與潛行最佳實踐)

This skill codifies the architectural rules and best practices for browser automation within the harness, combining **AX-Tree Ref-First Targeting**, **Framework-Safe Controlled Input Writes**, and **Stealth Fallback Strategies**.

---

## 1. Key Architectural Principles

### 1. Ref-First AX-Tree Targeting (`[eN]`)
- **Principle**: In Single Page Applications (SPAs), layout reflows and DOM re-renders invalidate raw viewport coordinates `@(x,y)` rapidly.
- **Rule**: Always prefer targeting interactive elements by stable accessibility refs (`[eN]`). Position coordinates MUST be dynamically re-resolved at the exact instant of action execution.
- **Stale Ref Recovery**: If an action returns `"ref is stale"`, do NOT blindly retry. Immediately issue a fresh snapshot to obtain updated `[eN]` refs.

### 2. Framework-Safe Input Writes (`browser_fill` pattern)
- **Principle**: Direct DOM property mutation (e.g. `input.value = "val"`) is frequently intercepted and reverted by React, Vue, or Angular state management.
- **Rule**: Input mutation MUST use the native prototype setter (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set`) and explicitly dispatch bubbling `input` and `change` events.

### 3. Token-Efficient Page Diffing vs Screenshots
- **Principle**: Taking full-page screenshots for every action consumes excessive vision tokens and slows execution.
- **Rule**: Verify mutating actions by reading returned **Page Changes (Diffs)** (e.g., added/removed `[eN]` elements or status text changes). Use visual screenshots strictly as a last resort for rendering verification.

### 4. Dual-Engine Fallback Architecture
- **Standard Local/CDP Browser**: Use for authenticated user sessions, internal tools, and standard web apps.
- **Camofox Stealth Browser (`camofox-stealth`)**: Use when facing anti-bot WAFs (Cloudflare Turnstile, Akamai, Datadome, Google /sorry captcha walls).

---

## 2. Decision Flowchart

```
                          [Need Web Task]
                                 │
                 Is target behind Cloudflare / WAF?
                                 │
                   ┌─────────────┴─────────────┐
                  YES                          NO
                   │                           │
         [camofox-stealth]           [Standard CDP / Browser]
         • Stealth Fingerprint       • Real Profile & Cookies
         • Captcha Bypass            • AX-Tree Ref-First ([eN])
         • Isolated Recon Tab        • Framework-Safe Fill
```

---

## 3. Tool Selection Reference

| Purpose | Recommended Tool / Pattern | Key Benefit |
| :--- | :--- | :--- |
| **Inspect Page Structure** | `browser_snapshot` / AX-Tree | Provides stable `[eN]` refs & coordinates |
| **Read Formatted Content** | `browser_read_page` / Reader Mode | Strips boilerplate, zero vision token cost |
| **Form Filling** | `browser_fill` / Native Setter | Prevents React/Vue value reversion |
| **WAF / Captcha Bypass** | `pi-skills/optional/camofox-stealth` | Bypasses Cloudflare & bot protection |
| **Visual Render Check** | `browser_screenshot` | Use ONLY when pixel layout verification is needed |
```
