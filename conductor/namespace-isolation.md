# 📜 Implementation Plan: Namespace Isolation (Harness Command Prefix)

## 🎯 Objective
Resolve command name collisions between the Harness and globally installed extensions (e.g., `oh-my-gemini-cli`) by migrating all distilled commands to a dedicated `h:` namespace.

## 🔍 Root Cause Analysis
- **Problem**: The Harness currently uses source-based prefixes (`omg`, `aibdd`, `addy`) for commands.
- **Conflict**: When a user installs the full community extension (e.g., `oh-my-gemini-cli`), Gemini CLI detects two providers for `/omg:team` and renames the workspace version to `/workspace.omg:team` while printing a warning.
- **Impact**: UX confusion and persistent "Conflicts detected" warnings.

## 🛠️ Proposed Solution
Implement **Namespace Isolation**:
1.  **Unified Prefix**: Change all command prefixes in `core/manifest.json` to `h` (Harness).
2.  **Clean Command Registry**: Ensure `/h:team`, `/h:kickoff`, etc., are the only entry points provided by the Harness.
3.  **Update Projections**: Re-generate configurations for Pi, Gemini, and Claude to reflect the new namespace.
4.  **Update Documentation**: Adjust `GEMINI.md` and `README.md` references.

## 📋 Implementation Steps

### Phase 1: Core Configuration
- [ ] **Update `core/manifest.json`**: Change `prefix` from `omg`, `aibdd`, etc., to `h` for all commands.
- [ ] **Update `scripts/generator.py`**: Update the hardcoded `GEMINI.md` template to use the new `/h:` commands in the examples.

### Phase 2: Projection & Mapping
- [ ] **Run `python scripts/generator.py`**: Re-generate the `.toml` and `.md` command proxies under the `h` directory.
- [ ] **Run `python scripts/mapper.py`**: Re-link the updated assets.

### Phase 3: Documentation
- [ ] **Update `README.md`**: Update the "常用指令" (Slash Commands) section.

## ✅ Verification
1.  Restart `gemini` CLI.
2.  Verify no "Conflicts detected" warning appears.
3.  Type `/h:` and verify the list of commands.
4.  Run `/h:team` to confirm functionality.

---
*Note: This makes the project robust against future conflicts with other community tools.*
