# CK's Pi Code Agent Harness - Developer Guide

## 🌐 Language
中文回應一律使用臺灣慣用之正體中文（術語對照詳見 [pi-rules/AGENTS.md](pi-rules/AGENTS.md) 第 0 節）；程式碼與 commit 訊息維持英文。

## 🛠️ Build & Setup Commands
* Run setup script: `python scripts/setup.py` (Interactive CLI)
* Restore configurations directly: `python scripts/setup.py --mode restore`
* Pull/Update submodules: `git submodule update --init --recursive`

## 🧪 Testing Commands
* Run tests (zero-dependency, stdlib unittest): `python -m unittest discover -s tests`

## 📌 CRITICAL Guidelines & Philosophy (Must Read First)
Before planning any optimizations, refactoring, or modifications to this repository, you **MUST** read and fully comprehend the following documentation to align with our engineering guidelines:
1. **[Core Concepts](docs/core/CORE_CONCEPTS.md)**: Understand the actual layout, integrated submodules, and CASE-aligned environment governance.
2. **[Distillation Guide](docs/core/DISTILLATION_GUIDE.md)**: Adhere strictly to the **Anti-Bragging**, **No passive/zombie config**, and **Platform-agnostic default** constraints.

## ✅ Evidence-Based Completion (實測有證據)
**Never claim something is done, fixed, or working without running the actual thing and observing the result.** "Should work", "looks correct", or "the code is right" are not evidence — only observed output is. This is the soul of this repo; violating it is the most serious failure here.

* **Test the real entry path, cold.** Exercise the path a fresh user actually hits — the first-use / server-down / clean-clone state — not the already-warm state you happened to set up. (Scar: `web_search` "worked" only because the backend was started manually first; the cold `spawn sh ENOENT` path was never tested and was broken for every new machine.)
* **"Green on my machine" is not proof.** Environments differ — PATH, gitignored files, OS. Reproduce the target condition before claiming pass. (Scar: a test read the gitignored `pi-config/settings.json`; it passed locally and broke on every fresh CI checkout.)
* **Show the evidence.** When reporting done, quote the actual command and its actual output. If you did not run it, say so plainly — do not imply verification you did not perform.
* **Numbers and claims come from a run at write-time.** Any concrete number or success claim in a report or **commit message** ("N tests pass", "covers X files", "3× faster") must come from an actual run at the moment you write it — never a prediction or memory. Run first, use the real value; if you can't verify it then, don't state a specific number. (Scar: a commit said "125 tests" — the real run was 127.)
* **CI is a feature, not noise.** A red CI that catches a real defect is doing its job; fix the defect, do not dismiss the signal.

## 🧭 Methodology-First (方法論優先)
This repo bundles many **methodology skills**; they only add value when invoked at the right moment — otherwise they are unused shells (same lesson as camofox: a capability that is never triggered is as good as absent). **Process skill first (sets the approach), then domain skill (executes).** Before non-trivial work: new/creative work → `brainstorming` then a plan; a bug → `systematic-debugging`; implementing → `test-driven-development`; a complex multi-step task → `planning-with-files`; a decision with trade-offs → `thinking-frameworks` / `mece-autopilot` / `qiushi`. Do not skip the method and dive straight into code. (Full routing: `pi-rules/AGENTS.md` §10.)

## 🚫 Forbidden Anti-Patterns
* **No Marketing/Hyperbole**: Do not use boasting words like "master-class", "revolutionary", or "15+ top repos". Speak plain, objective engineering truths.
* **No Zombie Configs**: Never register mock or empty extension files in `settings.json`. Every registered item must be active and tested.
* **No OS-Specific Hardcoding**: Do not put machine-specific paths (e.g. `C:\Program Files\Git...`) inside shared template configuration files. Use `setup.py` for runtime injection.
* **Shell & Execution**: Pi Coding Agent executes commands natively using `bash` (even on Windows). Ensure all harness configurations, scripts, and commands are strictly compatible with bash syntax rather than CMD/PowerShell.
