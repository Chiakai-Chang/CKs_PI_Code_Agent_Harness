---
name: minimal-prompt-guide
description: Principles for system prompt minimization (~80 tokens target), attention optimization, multi-language internationalization (i18n), and cross-platform execution.
tools: read, grep, find, ls, bash
---

# Minimal System Prompt & High-Efficiency Execution Guide (極簡系統提示與高效執行指南)

This skill codifies the rules for **System Prompt Minimization**, **Attention Focus Optimization**, and **Multi-Language Cross-Platform Execution** within the harness.

---

## 1. Minimal System Prompt Architecture (~80 Tokens Goal)

### 1. The Token Bloat Problem
- **Problem**: Traditional AI harnesses attach 15,000 to 28,000 tokens of system prompts (heavy rules, complex schemas, roleplay text).
- **Consequence**: High Time-To-First-Token (2-10s TTFT), high cost per request, and model attention distraction away from the user's actual code.

### 2. Minimization Principles
- **Rule**: Keep system prompts concise and focused (~80-200 tokens). Rely on a small set of core tools (`read`, `write`, `edit`, `bash`).
- **Rule**: Move non-essential rules into on-demand skills that are loaded only when relevant to the current task.

---

## 2. Multi-Language & Internationalization (i18n) Support

- **Rule**: Harness skills and feedback messages should respect the user's natural language locale (e.g. English, Traditional Chinese, Japanese, etc.).
- **Rule**: Markdown documentation and reports should maintain clear, accessible headings and structured code snippets across language targets.

---

## 3. Cross-Platform Safe Execution (Windows / POSIX)

- **Rule**: All execution scripts and harness extensions MUST maintain strict cross-platform compatibility:
  - Never hardcode Windows drive letters (`C:\...`) or POSIX root paths (`/home/...`) in tracked configuration files.
  - Use `os.path.join()` or standard POSIX paths within scripts.
  - Provide corresponding `.sh` (POSIX) and `.bat` (Windows) scripts for interactive launchers.

---

## 4. Summary Checklist for Harness Efficiency

1. Is the system prompt trimmed of non-essential instructions?
2. Are heavy domain rules encapsulated in on-demand skills?
3. Do script paths and shell executions run cleanly on both Windows and Linux/macOS?
