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

## 4. Self-Correction & Bounded Optimization (SkillOpt & C.A.S.E. Protocol)
To prevent infinite loops and improve success rates during debugging or tool failures:
*   **Rejected Memory**: If a command or test fails, record the failed approach and the exact error output in `.pi/rejected_attempts.json` or `findings.md`.
*   **Bounded Correction**: Before retrying, read the rejected attempts to ensure the new approach does not repeat previous errors. Modify only the specific code or parameters that failed.
*   **3-Strike Cap**: Limit consecutive retries of the same task to 3 attempts. On the 3rd failure, stop, write the failure log to `findings.md`, and escalate to the user with a summary.
*   **C.A.S.E. & Planning-with-Files Nesting**: When C.A.S.E. is active (indicated by `CASE.md` or `00_Constitution`), you MUST nest your `task_plan.md`, `findings.md`, and `progress.md` (from `planning-with-files`) INSIDE your active task directory (e.g. `02_Task_Queue/Task_<NNN>_<slug>/`) rather than the workspace root. Use `status.txt` to manage micro-state transitions (`IN_PROGRESS` -> `REVIEW`).
*   **Loop Engineering (Loopy Protocol)**: When executing or designing repeatable workflows (e.g. docs sync, test expansion, migrations), model them as bounded loops. Define: (1) target objective, (2) verification check, (3) feedback action, and (4) terminal/escalation conditions. Check catalog recommendations before inventing a new loop.
*   **Genetic Gating & PR Isolation (GEPA Protocol)**: When proposing a permanent optimization or modification to an agent skill (e.g., `SKILL.md`), NEVER apply it directly to the active configuration. Instead, create a separate git branch (`evolve/skill-name`), perform sandboxed trials, and present the final version to the user as a Git Diff/PR for explicit review and validation.

## 5. Persistent Knowledge Base & Cognitive Synergy (LLM Wiki & Graphify Protocol)
When accumulating knowledge, research papers, design decisions, or codebase architecture:
*   **Compilation over RAG**: Treat the LLM as a librarian. When a new raw source or reference document is introduced, compile it once into a persistent, interlinked wiki in the `wiki/` directory rather than re-reading raw files repeatedly.
*   **Keep it Atomic**: Ensure all wiki pages remain small (soft cap 400 lines) and are indexed in `wiki/index.md` or sharded indexes under `wiki/indexes/`.
*   **Graph Linking**: Use standard markdown wikilinks `[[page-name]]` to build a semantic knowledge graph. Use frontmatter variables (`type`, `tags`, `sources`, `updated`) on every wiki page.
*   **Code Graph Alignment (Graphify Integration)**: Before answering architecture or codebase questions, check whether `graphify-out/GRAPH_REPORT.md` exists. If so, read it first to navigate god nodes and community structures. If `wiki/index.md` exists alongside the graph, navigate the wiki instead of reading raw files. Run `graphify update .` (AST-only, no API cost) after code changes to keep the graph in sync.

## 6. Collective Skill Evolution (SkillClaw & Darwin Protocol)
When learning from sessions or optimizing local skills/rules:
*   **History ledger priority**: Before editing any existing skill or configuration (e.g. `SKILL.md`), you MUST search for its history records (`history/v*.md` or past commits/rationales). Explicitly document: what changed in each prior version, what evidence drove it, and whether later sessions suggested it helped or hurt.
*   **Summarize & Decide (SkillClaw + Darwin)**: Group session logs/rationales. Use `SkillClaw` to decide macro updates: `create_skill`, `improve_skill`, or `skip`. If a skill's prompts require micro-tuning, trigger `darwin-skill` to execute sandboxed mutation trials.
*   **Rigorous Self-Validation (GEPA + Qiushi Synergy)**: Before finalizing any skill optimization, define 1-3 validation scenarios from session evidence. Run a dry run or static simulation on a separate branch. Use `qiushi` logic to establish a clean control group comparison. Write validation logs to `history/v<N>_evidence.md` before merging via Git Diff.

## 7. Quality & Performance Harmony (UI/UX Pro Max & Addyosmani Protocol)
When implementing frontend designs and components:
*   **Design-Performance Budget**: Before writing CSS/JS under `ui-ux-pro-max`, read the performance budgets defined by `addyosmani-skills`. Ensure animations, gradients, and font imports do not breach LCP/CLS/FID targets.
*   **Automated Validation**: After design completion, run `browser-testing-with-devtools` in headless chrome to verify that aesthetic components do not regress loading speeds. Do not claim UX completion without performance telemetry evidence.
