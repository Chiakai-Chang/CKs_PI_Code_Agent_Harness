---
name: harness-factory-guide
description: Harness factory, repo scoring & security scanning standard for Pi Coding Agent Harness — Repo fit scoring, Darwin configuration evolution, smart cost routing, and default-deny MCP security auditing.
---

# Harness Factory & Security Audit Standard

This skill establishes the **Harness Factory & Security Audit Standard** distilled from MetaHarness (`metaharness`).

---

## 1. Repo Fit & Readiness Scoring (`harness score`)

Before initializing or generating a harness for any codebase, evaluate the project across 4 criteria:
1. **Harness Fit (0-100)**: Does the repo have clear build/test manifests and defined entry points?
2. **Build Predictability**: Are commands explicitly declared in `package.json`, `Makefile`, or `Cargo.toml` without implicit steps?
3. **Tool Safety**: Are tool grants scoped and default-deny?
4. **Estimated Cost Tier**: Can task subsets be routed to cheaper models without losing quality?

---

## 2. Darwin Configuration Evolution (`npm run evolve`)

The model weights remain frozen; the harness configuration evolves:
- Mutate prompt structures, tool permissions, and skill routing rules.
- Test each mutation in a local sandbox against regression test suites.
- Retain ONLY mutations that yield measurable improvements in test pass rate or token reduction.

---

## 3. MCP Default-Deny Security Scan (`mcp-scan`)

Treat MCP tool definitions with zero-trust security:
- **No Unrestricted Shell/Network**: Block wildcards (`*`) in execution permissions.
- **Audit Logging**: Require audit logs for sensitive file or command actions.
- **Timeout Enforcements**: Enforce strict timeouts (e.g. 30s) on external calls.
- **Secret Isolation**: Hardcoded API keys or unpinned dependencies trigger an immediate fail (Exit 1).

---

## 4. Defense Checklist

- [ ] Has repo fit scoring been conducted prior to major harness generation?
- [ ] Are all MCP tool configurations set to default-deny with explicit scopes?
- [ ] Does `python scripts/validate-config.py` pass cleanly with 0 errors?
