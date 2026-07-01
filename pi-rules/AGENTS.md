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

## 4. Self-Correction & Bounded Optimization (SkillOpt Protocol)
To prevent infinite loops and improve success rates during debugging or tool failures:
*   **Rejected Memory**: If a command or test fails, record the failed approach and the exact error output in `.pi/rejected_attempts.json` or `findings.md`.
*   **Bounded Correction**: Before retrying, read the rejected attempts to ensure the new approach does not repeat previous errors. Modify only the specific code or parameters that failed.
*   **3-Strike Cap**: Limit consecutive retries of the same task to 3 attempts. On the 3rd failure, stop, write the failure log to `findings.md`, and escalate to the user with a summary.
*   **Genetic Gating & PR Isolation (GEPA Protocol)**: When proposing a permanent optimization or modification to an agent skill (e.g., `SKILL.md`), NEVER apply it directly to the active configuration. Instead, create a separate git branch (`evolve/skill-name`), perform sandboxed trials, and present the final version to the user as a Git Diff/PR for explicit review and validation.

## 5. Persistent Knowledge Base (LLM Wiki Protocol)
When accumulating knowledge, research papers, design decisions, or codebase architecture:
*   **Compilation over RAG**: Treat the LLM as a librarian. When a new raw source or reference document is introduced, compile it once into a persistent, interlinked wiki in the `wiki/` directory rather than re-reading raw files repeatedly.
*   **Keep it Atomic**: Ensure all wiki pages remain small (soft cap 400 lines) and are indexed in `wiki/index.md` or sharded indexes under `wiki/indexes/`.
*   **Graph Linking**: Use standard markdown wikilinks `[[page-name]]` to build a semantic knowledge graph. Use frontmatter variables (`type`, `tags`, `sources`, `updated`) on every wiki page.
