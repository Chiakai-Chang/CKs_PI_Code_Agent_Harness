---
name: adversary-review
description: Conduct adversarial code review to uncover edge-case bugs, silent failures, missing exception handling, and unauthorized scope creep before merging code.
---

# Adversary Review Gate (對抗式代碼審查與極限校驗)

The **Adversary Review Gate** acts as an uncompromising quality checkpoint inspired by the `ultimate-pi` adversary reviewer agent. It stress-tests code changes against edge cases, boundary conditions, platform incompatibilities, and hidden regressions before code is accepted.

---

## 🛡️ Core Review Lens (七大對抗角度)

When conducting an adversary review, evaluate code changes strictly against these 7 critical angles:

### 1. Silent Exception & Masking Swallows
- **Check**: Are try/except blocks swallowing exceptions (`except: pass` without logging or recovery)?
- **Requirement**: Never mask runtime failures. All caught exceptions must either be logged, handled with explicit fallback logic, or re-raised with contextual error details.

### 2. Boundary & Null Safety
- **Check**: Are function parameters, array indices, dictionary keys, and API responses verified before access?
- **Requirement**: Prevent `AttributeError`, `TypeError`, `IndexError`, and `KeyError` by explicitly validating input presence and type constraints.

### 3. Cross-Platform & Environment Leaks
- **Check**: Are OS-specific file paths (e.g. `C:\...` or `/usr/local/bin`) hardcoded into shared codebase files?
- **Requirement**: Paths must be dynamic (`pathlib.Path`, `os.path.join`, `os.path.expanduser`), and platform-dependent execution must be safely guarded.

### 4. Scope Creep & Plan Compliance
- **Check**: Did the code implementation introduce unrequested refactors, unnecessary dependency additions, or modifications outside the approved plan?
- **Requirement**: Keep diffs surgical and focused strictly on the assigned task scope.

### 5. Resource Leak & Locking
- **Check**: Are file handles, database connections, subprocesses, or temporary directories left open or uncleaned?
- **Requirement**: Use context managers (`with` statements) or explicit cleanup routines (`try...finally`).

### 6. Destructive Shell & Command Safety
- **Check**: Are shell invocations using raw string interpolation that could lead to command injection or accidental data wiping (`rm -rf`, `DROP TABLE`)?
- **Requirement**: Validate inputs and parameters before passing them to shell execution.

### 7. Verifiable Evidence
- **Check**: Is there concrete, empirical runtime proof (test output, build log, execution output) demonstrating that the code works?
- **Requirement**: Never claim success without executing verification commands and inspecting output.

---

## 📋 Adversary Verdict Output Format

When returning a review verdict, output a clear, structured Markdown report:

```markdown
### 🛡️ Adversary Review Verdict

- **Status**: [PASSED | IMPLEMENTATION_GAP | REJECTED]
- **Target Files**: `[files modified]`
- **Findings**:
  1. ❌ **[Category]**: Description of issue or edge case.
     - **Location**: `path/to/file.py:L42`
     - **Remediation**: Recommended fix.
- **Verification Evidence**: `[command run and outcome]`
```
