# CK's Pi Code Agent Harness - Developer Guide

## 🛠️ Build & Setup Commands
* Run setup script: `python scripts/setup.py` (Interactive CLI)
* Restore configurations directly: `python scripts/setup.py --mode restore`
* Pull/Update submodules: `git submodule update --init --recursive`

## 🧪 Testing Commands
* Run tests: (Add testing command if applicable in future, currently experimental harness)

## 📌 CRITICAL Guidelines & Philosophy (Must Read First)
Before planning any optimizations, refactoring, or modifications to this repository, you **MUST** read and fully comprehend the following documentation to align with our engineering guidelines:
1. **[Core Concepts (docs/core/CORE_CONCEPTS.md)](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/docs/core/CORE_CONCEPTS.md)**: Understand the actual layout, integrated submodules, and CASE-aligned environment governance.
2. **[Distillation Guide (docs/core/DISTILLATION_GUIDE.md)](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/docs/core/DISTILLATION_GUIDE.md)**: Adhere strictly to the **Anti-Bragging**, **No passive/zombie config**, and **Platform-agnostic default** constraints.

## 🚫 Forbidden Anti-Patterns
* **No Marketing/Hyperbole**: Do not use boasting words like "master-class", "revolutionary", or "15+ top repos". Speak plain, objective engineering truths.
* **No Zombie Configs**: Never register mock or empty extension files in `settings.json`. Every registered item must be active and tested.
* **No OS-Specific Hardcoding**: Do not put machine-specific paths (e.g. `C:\Program Files\Git...`) inside shared template configuration files. Use `setup.py` for runtime injection.
