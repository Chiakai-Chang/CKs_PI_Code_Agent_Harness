# Workspace Guidelines for Gemini CLI & Antigravity Agents

## Mandatory Onboarding Steps
Whenever initialized, you must immediately read:
- [CORE_CONCEPTS.md](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/docs/core/CORE_CONCEPTS.md) (Engineering goals and submodules mapping)
- [DISTILLATION_GUIDE.md](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/docs/core/DISTILLATION_GUIDE.md) (Core rules, platform agnostic rules, anti-bragging)

## Key Constraints
- **Anti-Bragging**: Refrain from using promotional adjectives or claims that lack functional evidence. Focus on experimental facts.
- **Config Hygiene**: Do not register empty/placeholder TypeScript extensions in `settings.json` templates.
- **Cross-Platform Safety**: Windows paths (e.g. `C:\...`) must never be hardcoded in files under `pi-config/`. Instead, implement dynamic setup logic in `scripts/setup.py` and run it during install.
- **C.A.S.E. Alignment**: Align extensions design with the C.A.S.E. Framework repository principles.
