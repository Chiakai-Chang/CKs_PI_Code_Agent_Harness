# Agent Instructions

## 1. Windows + Git Bash Environment Rules (CRITICAL)
Even though the operating system is Windows (e.g., CWD/paths look like `C:/...` or `D:/...`), the underlying shell for the `bash` tool is configured as **Git Bash (bash.exe)**.
*   **Path Formatting**: ALWAYS use forward slashes (`/`) for paths when writing commands or referring to files (e.g., `ls src/core` instead of `ls src\core`).
*   **UNIX Utilities**: ALWAYS use standard UNIX utilities (`ls`, `grep`, `find`, `cp`, `mv`, `rm`, `cat`, `mkdir`, `rmdir`, etc.) in the `bash` tool.
*   **No PowerShell/CMD**: NEVER use PowerShell or CMD commands (e.g., `Get-ChildItem`, `gc`, `dir`, `copy`, `move`, `del`, `type`, `md`, or `%APPDATA%`).
*   **Chaining Commands**: Use `&&`, `||`, and `;` to chain commands instead of PowerShell's `;` or CMD's `&`.

## 2. Agent Orchestration Routing
For complex tasks, delegate to specialised agents under `D:/MyProject/everything-claude-code/agents`:
*   Use `planner` for implementation planning.
*   Use `architect` for system design.
*   Use `tdd-guide` for new features or bug fixes.
*   Use `code-reviewer` after writing code.
*   Use `security-reviewer` before commits.

## 3. CLI Design Standards
Follow compact output rules:
*   Pass `--compact` or `--select` flags where supported to minimize data transfer.
*   Check exit codes for automated retry strategies.
