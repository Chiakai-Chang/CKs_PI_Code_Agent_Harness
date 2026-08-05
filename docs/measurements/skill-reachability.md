# 技能可達性全掃

由 `scripts/audit-skill-reach.py` 產生於 2026-08-06 07:30。**不要手改** —— 重跑即可更新。

core 層來源:實測 prompt(C:/Users/User/AppData/Local/Temp/claude/D--MyProject-CKs-PI-Code-Agent-Harness/8c24d11d-f80e-4106-94eb-d5d96888c4da/scratchpad/pd/prompt.txt)

## 為什麼要有這份文件

Pi 把技能分兩層寫進 system prompt:core 層有 name + description + location,
catalog 層只有名字加一個 JSON 檔路徑。**描述是請求靠詞彙找到技能的唯一途徑**,
所以一個技能落在哪一層,決定它到底能不能被用到。

2026-08-06 dump 實際 prompt 才發現:`case-framework`(擁有者自己寫的任務佇列協定,
內含一整輪設計會議剛收斂要重造的每一個機制)就躺在沒有描述的那 122 個裡,
README 畫的 Layer 1 三個技能也全部在裡面。

## 總計

| 層 | 數量 | 模型看得到什麼 |
|---|---:|---|
| core | 43 | 名稱、描述、絕對路徑 —— 可靠詞彙發現 |
| catalog | 122 | 只有名稱 —— 需先讀 catalog JSON 再讀 SKILL.md |

## core 層(有描述,43)

| 技能 | 來源 | 描述 |
|---|---|---|
| `caveman` | external/caveman | Ultra-compressed communication mode. Cuts token usage ~75% by speaking like caveman while keeping full technical accuracy. Supports intensity levels: lite, ful… |
| `mece-autopilot` | external/mece-autopilot | Perform structured, dynamic MECE (Mutually Exclusive, Collectively Exhaustive) roundtable discussions to resolve complex engineering, architecture, or business… |
| `contradiction-analysis` | external/qiushi-skill | 触发：当问题复杂、存在多个冲突因素、优先级不清，或你不知道应该先解决什么时调用；常见信号包括 trade-off、瓶颈、根因不明、主次不清、多个问题互相牵制。 English: Trigger when a problem contains competing forces, unclear priorities, … |
| `brainstorming` | external/superpowers | You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, require… |
| `dispatching-parallel-agents` | external/superpowers | Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies |
| `executing-plans` | external/superpowers | Use when you have a written implementation plan to execute in a separate session with review checkpoints |
| `finishing-a-development-branch` | external/superpowers | Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting str… |
| `receiving-code-review` | external/superpowers | Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical… |
| `requesting-code-review` | external/superpowers | Use when completing tasks, implementing major features, or before merging to verify work meets requirements |
| `subagent-driven-development` | external/superpowers | Use when executing implementation plans with independent tasks in the current session |
| `systematic-debugging` | external/superpowers | Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes |
| `test-driven-development` | external/superpowers | Use when implementing any feature or bugfix, before writing implementation code |
| `using-git-worktrees` | external/superpowers | Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via … |
| `using-superpowers` | external/superpowers | Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions |
| `verification-before-completion` | external/superpowers | Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output b… |
| `writing-plans` | external/superpowers | Use when you have a spec or requirements for a multi-step task, before touching code |
| `writing-skills` | external/superpowers | Use when creating new skills, editing existing skills, or verifying skills work before deployment |
| `yes` | external/yes.md | Use when any task involves modifying files, configs, databases, or deployments. Use when debugging hits 2+ failures. Use when about to guess or assume without … |
| `code-review` | ~/.agents/skills/(外來) | Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes — Standards (does the code follow this repo&apos;s documented coding… |
| `codebase-design` | ~/.agents/skills/(外來) | Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module&apos;s interface, find deepening opportunities, decide wher… |
| `design-an-interface` | ~/.agents/skills/(外來) | Generate multiple radically different interface designs for a module using parallel sub-agents. Use when user wants to design an API, explore interface options… |
| `diagnosing-bugs` | ~/.agents/skills/(外來) | Diagnosis loop for hard bugs and performance regressions. Use when the user says &quot;diagnose&quot;/&quot;debug this&quot;, or reports something broken/throw… |
| `domain-modeling` | ~/.agents/skills/(外來) | Build and sharpen a project&apos;s domain model. Use when the user wants to pin down domain terminology or a ubiquitous language, record an architectural decis… |
| `find-skills` | ~/.agents/skills/(外來) | Helps users discover and install agent skills when they ask questions like &quot;how do I do X&quot;, &quot;find a skill for X&quot;, &quot;is there a skill th… |
| `git-guardrails-claude-code` | ~/.agents/skills/(外來) | Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute. Use when user wants to prevent destr… |
| `grilling` | ~/.agents/skills/(外來) | Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any &apos;grill&apos; trigger phras… |
| `hallmark` | ~/.agents/skills/(外來) | Anti-AI-slop design skill for greenfield pages, audits, redesigns, and design extraction from URLs or screenshots. Use when the user asks to build a new app or… |
| `migrate-to-shoehorn` | ~/.agents/skills/(外來) | Migrate test files from `as` type assertions to @total-typescript/shoehorn. Use when user mentions shoehorn, wants to replace `as` in tests, or needs partial t… |
| `obsidian-vault` | ~/.agents/skills/(外來) | Search, create, and manage notes in the Obsidian vault with wikilinks and index notes. Use when user wants to find, create, or organize notes in Obsidian. |
| `prototype` | ~/.agents/skills/(外來) | Build a throwaway prototype to answer a design question. Use when the user wants to sanity-check whether a state model or logic feels right, or explore what a … |
| `qa` | ~/.agents/skills/(外來) | Interactive QA session where user reports bugs or issues conversationally, and the agent files GitHub issues. Explores the codebase in the background for conte… |
| `request-refactor-plan` | ~/.agents/skills/(外來) | Create a detailed refactor plan with tiny commits via user interview, then file it as a GitHub issue. Use when user wants to plan a refactor, create a refactor… |
| `research` | ~/.agents/skills/(外來) | Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, … |
| `resolving-merge-conflicts` | ~/.agents/skills/(外來) | Use when you need to resolve an in-progress git merge/rebase conflict. |
| `scaffold-exercises` | ~/.agents/skills/(外來) | Create exercise directory structures with sections, problems, solutions, and explainers that pass linting. Use when user wants to scaffold exercises, create ex… |
| `setup-pre-commit` | ~/.agents/skills/(外來) | Set up Husky pre-commit hooks with lint-staged (Prettier), type checking, and tests in the current repo. Use when user wants to add pre-commit hooks, set up Hu… |
| `tdd` | ~/.agents/skills/(外來) | Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions &quot;red-green-refactor&quot;, or wants integration tests. |
| `agents-best-practices` | ~/.pi/agent/skills/(自動探索) | Use this skill when designing, generating an MVP blueprint for, auditing, refactoring, or explaining an agentic harness for any domain. Covers provider-neutral… |
| `darwin-skill` | ~/.pi/agent/skills/(自動探索) | Darwin Skill 2.0 (达尔文.skill 2.0): autonomous skill optimizer, v2.0 integrates Microsoft Research SkillLens (arXiv 2605.23899) 9-dim rubric + SkillOpt (arXiv 26… |
| `research-task-routing` | ~/.pi/agent/skills/(自動探索) | Use when a request asks for research, a market survey, competitive analysis, a landscape review, a feasibility study, a technology comparison, an audit, or any… |
| `chrome-cdp` | 本 harness pi-skills/ | Interact with local Chrome browser session (only on explicit user approval after being asked to inspect, debug, or interact with a page open in Chrome) |
| `dev-browser` | 本 harness pi-skills/ | Browser automation with persistent page state. Use when users ask to navigate websites, fill forms, take screenshots, extract web data, test web apps, or autom… |
| `graphify` | 本 harness pi-skills/ | Use for analyzing codebase structure, AST relationships, module calls, or to query the codebase graph (specifically if graphify-out/ exists). Provides tools to… |

### 其中不屬於本 harness 的(19)

由鄰居工具安裝在 `~/.agents/skills/`。**本 harness 的 tiering 降不了它們** ——
降級只作用在自己註冊的技能上。它們佔著描述層,與 harness 自己的技能搶同一類請求。

- `code-review`
- `codebase-design`
- `design-an-interface`
- `diagnosing-bugs`
- `domain-modeling`
- `find-skills`
- `git-guardrails-claude-code`
- `grilling`
- `hallmark`
- `migrate-to-shoehorn`
- `obsidian-vault`
- `prototype`
- `qa`
- `request-refactor-plan`
- `research`
- `resolving-merge-conflicts`
- `scaffold-exercises`
- `setup-pre-commit`
- `tdd`

## catalog 層(只有名字,122)

描述欄是從各自的 `SKILL.md` frontmatter 讀出來的 —— **模型在 prompt 裡看不到這一欄**。
列在這裡是為了讓人看得出哪些能力其實存在。

### ECC 子模組(65)

| 技能 | 描述(模型看不到) |
|---|---|
| `agent-architecture-audit` | Full-stack diagnostic for agent and LLM applications. Audits the 12-layer agent stack for wrapper regression, memory pollution, tool discipline failures, hidden repair loops, and rendering corruption… |
| `agent-harness-construction` | Design and optimize AI agent action spaces, tool definitions, and observation formatting for higher completion rates. |
| `agent-introspection-debugging` | Structured self-debugging workflow for AI agent failures using capture, diagnosis, contained recovery, and introspection reports. |
| `agent-sort` | Build an evidence-backed ECC install plan for a specific repo by sorting skills, commands, rules, hooks, and extras into DAILY vs LIBRARY buckets using parallel repo-aware review passes. Use when ECC… |
| `agentic-engineering` | Operate as an agentic engineer using eval-first execution, decomposition, and cost-aware model routing. |
| `agentic-os` | Build persistent multi-agent operating systems on Claude Code. Covers kernel architecture, specialist agents, slash commands, file-based memory, scheduled automation, and state management without ext… |
| `ai-first-engineering` | Engineering operating model for teams where AI agents generate a large share of implementation output. |
| `ai-regression-testing` | Regression testing strategies for AI-assisted development. Sandbox-mode API testing without database dependencies, automated bug-check workflows, and patterns to catch AI blind spots where the same m… |
| `autonomous-loops` | "Patterns and architectures for autonomous Claude Code loops — from simple sequential pipelines to RFC-driven multi-agent DAG systems." |
| `benchmark-optimization-loop` | Use when the user asks to make something faster, try many variants, run recursive optimization, benchmark latency/throughput/cost, or choose the best implementation by repeated measured tests. |
| `blueprint` | >- Turn a one-line objective into a step-by-step construction plan for multi-session, multi-agent engineering projects. Each step has a self-contained context brief so a fresh agent can execute it co… |
| `claude-devfleet` | Orchestrate multi-agent coding tasks via Claude DevFleet — plan projects, dispatch parallel agents in isolated worktrees, monitor progress, and read structured reports. |
| `code-tour` | Create CodeTour `.tour` files — persona-targeted, step-by-step walkthroughs with real file and line anchors. Use for onboarding tours, architecture walkthroughs, PR tours, RCA tours, and structured "… |
| `configure-ecc` | Interactive installer for Everything Claude Code — guides users through selecting and installing skills and rules to user-level or project-level directories, verifies paths, and optionally optimizes … |
| `content-hash-cache-pattern` | Cache expensive file processing results using SHA-256 content hashes — path-independent, auto-invalidating, with service layer separation. |
| `continuous-agent-loop` | Patterns for continuous autonomous agent loops with quality gates, evals, and recovery controls. |
| `continuous-learning` | "[DEPRECATED - use continuous-learning-v2] Legacy v1 stop-hook skill extractor. v2 is a strict superset with instinct-based, project-scoped, hook-reliable learning. Do not invoke v1; route continuous… |
| `continuous-learning-v2` | Instinct-based learning system that observes sessions via hooks, creates atomic instincts with confidence scoring, and evolves them into skills/commands/agents. v2.1 adds project-scoped instincts to … |
| `cost-aware-llm-pipeline` | Cost optimization patterns for LLM API usage — model routing by task complexity, budget tracking, retry logic, and prompt caching. |
| `council` | Convene a four-voice council for ambiguous decisions, tradeoffs, and go/no-go calls. Use when multiple valid paths exist and you need structured disagreement before choosing. |
| `data-scraper-agent` | Build a fully automated AI-powered data collection agent for any public source — job boards, prices, news, GitHub, sports, anything. Scrapes on a schedule, enriches data with a free LLM (Gemini Flash… |
| `data-throughput-accelerator` | Use when large data ingestion, backfill, export, ETL, warehouse loading, manifest catch-up, or table synchronization needs to become much faster while preserving data correctness. |
| `defi-amm-security` | Security checklist for Solidity AMM contracts, liquidity pools, and swap flows. Covers reentrancy, CEI ordering, donation or inflation attacks, oracle manipulation, slippage, admin controls, and inte… |
| `django-security` | Django security best practices, authentication, authorization, CSRF protection, SQL injection prevention, XSS prevention, and secure deployment configurations. |
| `dynamic-workflow-mode` | "Design task-local harnesses, eval gates, and reusable skill extraction for Claude dynamic workflow mode and other adaptive agent harnesses." |
| `e2e-testing` | Playwright E2E testing patterns, Page Object Model, configuration, CI/CD integration, artifact management, and flaky test strategies. |
| `ecc-guide` | Guide users through ECC's current agents, skills, commands, hooks, rules, install profiles, and project onboarding by reading the live repository surface before answering. |
| `ecc-recipes` | "Map a described workflow to the right ECC command-GROUP with run-order and stop condition, and browse all command-group recipe families. Adds a family-grouping + run-order + when-to-stop layer on to… |
| `ecc-tools-cost-audit` | Evidence-first ECC Tools burn and billing audit workflow. Use when investigating runaway PR creation, quota bypass, premium-model leakage, duplicate jobs, or GitHub App cost spikes in the ECC Tools r… |
| `enterprise-agent-ops` | Operate long-lived agent workloads with observability, security boundaries, and lifecycle management. |
| `error-handling` | Patterns for robust error handling across TypeScript, Python, and Go. Covers typed errors, error boundaries, retries, circuit breakers, and user-facing error messages. |
| `eval-harness` | Formal evaluation framework for Claude Code sessions implementing eval-driven development (EDD) principles |
| `evm-token-decimals` | Prevent silent decimal mismatch bugs across EVM chains. Covers runtime decimal lookup, chain-aware caching, bridged-token precision drift, and safe normalization for bots, dashboards, and DeFi tools. |
| `healthcare-phi-compliance` | Protected Health Information (PHI) and Personally Identifiable Information (PII) compliance patterns for healthcare applications. Covers data classification, access control, audit trails, encryption,… |
| `hipaa-compliance` | HIPAA-specific entrypoint for healthcare privacy and security work. Use when a task is explicitly framed around HIPAA, PHI handling, covered entities, BAAs, breach posture, or US healthcare complianc… |
| `hookify-rules` | This skill should be used when the user asks to create a hookify rule, write a hook rule, configure hookify, add a hookify rule, or needs guidance on hookify rule syntax and patterns. |
| `iterative-retrieval` | Pattern for progressively refining context retrieval to solve the subagent context problem |
| `laravel-security` | Laravel security best practices — authentication, authorization, Eloquent safety, CSRF, XSS prevention, API security, and secure deployment configurations. |
| `latency-critical-systems` | Use for latency-sensitive systems such as realtime dashboards, market data, streaming agents, execution gateways, queues, caches, or HFT-like infrastructure where freshness and p95 latency matter. |
| `llm-trading-agent-security` | Security patterns for autonomous trading agents with wallet or transaction authority. Covers prompt injection, spend limits, pre-send simulation, circuit breakers, MEV protection, and key handling. |
| `nanoclaw-repl` | Operate and extend NanoClaw v2, ECC's zero-dependency session-aware REPL built on claude -p. |
| `nodejs-keccak256` | Prevent Ethereum hashing bugs in JavaScript and TypeScript. Node's sha3-256 is NIST SHA3, not Ethereum Keccak-256, and silently breaks selectors, signatures, storage slots, and address derivation. |
| `parallel-execution-optimizer` | Use when the user wants a task done much faster through parallel work, concurrent agents, batched tool calls, isolated worktrees, or many independent verification lanes without losing correctness. |
| `perl-security` | Comprehensive Perl security covering taint mode, input validation, safe process execution, DBI parameterized queries, web security (XSS/SQLi/CSRF), and perlcritic security policies. |
| `plankton-code-quality` | "Write-time code quality enforcement using Plankton — auto-formatting, linting, and Claude-powered fixes on every file edit via hooks." |
| `production-audit` | Local-evidence production readiness audit for shipped apps, pre-launch reviews, post-merge checks, and "what breaks in prod?" questions without sending repo data to an external audit service. |
| `prompt-optimizer` | >- Analyze raw prompts, identify intent and gaps, match ECC components (skills/commands/agents/hooks), and output a ready-to-paste optimized prompt. Advisory role only — never executes the task itsel… |
| `quarkus-security` | Quarkus Security best practices for authentication, authorization, JWT/OIDC, RBAC, input validation, CSRF, secrets management, and dependency security. |
| `ralphinho-rfc-pipeline` | RFC-driven multi-agent DAG execution pattern with quality gates, merge queues, and work unit orchestration. |
| `recursive-decision-ledger` | Use when the user asks for repeated rollouts, marked decision processes, high-dimensional search, stochastic optimization, local-optima exploration, ensemble comparison, or recursive reasoning with a… |
| `regex-vs-llm-structured-text` | Decision framework for choosing between regex and LLM when parsing structured text — start with regex, add LLM only for low-confidence edge cases. |
| `search-first` | Research-before-coding workflow. Search for existing tools, libraries, and patterns before writing custom code. Invokes the researcher agent. |
| `security-bounty-hunter` | Hunt for exploitable, bounty-worthy security issues in repositories. Focuses on remotely reachable vulnerabilities that qualify for real reports instead of noisy local-only findings. |
| `security-review` | Use this skill when adding authentication, handling user input, working with secrets, creating API endpoints, or implementing payment/sensitive features. Provides comprehensive security checklist and… |
| `security-scan` | Scan your Claude Code configuration (.claude/ directory) for security vulnerabilities, misconfigurations, and injection risks using AgentShield. Checks CLAUDE.md, settings.json, MCP servers, hooks, a… |
| `skill-scout` | Search existing local, marketplace, GitHub, and web skill sources before creating a new skill. Use when the user wants to create, build, fork, or find a skill for a workflow. |
| `skill-stocktake` | "Use when auditing Claude skills and commands for quality. Supports Quick Scan (changed skills only) and Full Stocktake modes with sequential subagent batch evaluation." |
| `springboot-security` | Spring Security best practices for authn/authz, validation, CSRF, secrets, headers, rate limiting, and dependency security in Java Spring Boot services. |
| `strategic-compact` | Suggests manual context compaction at logical intervals to preserve context through task phases rather than arbitrary auto-compaction. |
| `tdd-workflow` | Use this skill when writing new features, fixing bugs, or refactoring code. Enforces test-driven development with 80%+ coverage including unit, integration, and E2E tests. |
| `team-agent-orchestration` | "Run team-based orchestration for agent squads using work items, ownership, agent Kanban, merge gates, and control pane handoffs." |
| `team-builder` | Interactive agent picker for composing and dispatching parallel teams |
| `token-budget-advisor` | >- Offers the user an informed choice about how much response depth to consume before answering. Use this skill when the user explicitly wants to control response length, depth, or token budget. TRIG… |
| `verification-loop` | "A comprehensive verification system for Claude Code sessions." |
| `windows-desktop-e2e` | E2E testing for Windows native desktop apps (WPF, WinForms, Win32/MFC, Qt) using pywinauto and Windows UI Automation. |

### 本 harness pi-skills/(18)

| 技能 | 描述(模型看不到) |
|---|---|
| `adversary-review` | Conduct adversarial code review to uncover edge-case bugs, silent failures, missing exception handling, and unauthorized scope creep before merging code. |
| `autonomous-experiment-guide` | Guidelines for autonomous experiment loops, statistical confidence evaluation (MAD), backpressure validation, and worktree isolation. |
| `browser-automation-guide` | Best practices for browser automation, AX-Tree ref-first targeting, framework-safe input writes, and stealth fallback strategy. |
| `camofox-stealth` | 網路偵察／動工前調研用的專業級隱身瀏覽器（camofox / camofox-browser / Camoufox 隱身瀏覽即用本技能，勿自行 npm install 或當 Node library import）。當任務涉及外部庫、未知或易過時的技術，或目標網站有強大機器人偵測（Cloudflare/登入牆）、或需極低 Token 消耗讀長頁時使用。以 curl 驅動本地釘版 camofox-… |
| `contrarian-review` | Contrarian Adversarial Review Gate for stress-testing designs, architectures, and decisions before locking plans. |
| `cua-commander` | 連接本地已安裝的 cua (Computer Use Agent) 服務。僅在您已安裝 Docker/QEMU 並啟動 cua 服務時使用。此技能提供指令範本，讓 Pi 成為 cua 服務的「指揮中心」。 |
| `deep-research-guide` | Deep web research using the deep_research tool, which runs each sub-question as its own isolated agent process and returns only the findings. Covers decomposition, when the fan-out is worth its wall-… |
| `grilling-protocol` | Product clarification and evidence verification standard for Pi Coding Agent Harness — One-question-at-a-time interview, ambiguity resolution, architectural trade-off evaluation, edge case coverage, … |
| `guardian-pipeline-guide` | Architectural standards for command guardians, structural workflow decomposition, and skill taxonomy classification. |
| `harness-factory-guide` | Harness factory, repo scoring & security scanning standard for Pi Coding Agent Harness — Repo fit scoring, Darwin configuration evolution, smart cost routing, and default-deny MCP security auditing. |
| `hello-reflect` | 自動化反思系統。在 Session 結束時自動掃描對話紀錄，擷取使用者的修正建議與偏好，並協助將其轉化為持久的專案規範（如 CLAUDE.md、.agents/AGENTS.md）。 |
| `ide-intelligence-guide` | IDE-wired intelligence & model-adapted edit standard for Pi Coding Agent Harness — Model-tuned diff formats, LSP diagnostics verification, and tiered model role routing. |
| `minimal-prompt-guide` | Principles for system prompt minimization (~80 tokens target), attention optimization, multi-language internationalization (i18n), and cross-platform execution. |
| `nothing-design` | This skill should be used when the user explicitly says "Nothing style", "Nothing design", "/nothing-design", or directly asks to use/apply the Nothing design system. NEVER trigger automatically for … |
| `subagent-orchestration-guide` | Architectural standards for subagent role specialization, model tiering (cheap/balanced/max), lineage-only context pruning, and trust-gated execution. |
| `thinking-frameworks` | 日常非瑣碎決策的快速心智模型自我檢查(反演/基準率/二階效應/機會成本/第一性原理/偏誤檢查/可證偽)。重取捨或多方利害請升級 mece-autopilot;辯證分析用 qiushi。純推理工具,不冒名真人、不給投資/醫療/法律建議。 |
| `tool-repair-guide` | Defensive rules and self-healing specifications for LLM tool call argument repairs, runtime fallbacks, and prompt-cache friendly error guidance. |
| `workflow-os-guide` | Comprehensive guide for Workflow OS patterns in Pi Coding Agent Harness — Pins/Gates/Steers architecture, phase tool allowlisting, deterministic handoff generation, and orphan skill detection. |

### external/taste-skill(13)

| 技能 | 描述(模型看不到) |
|---|---|
| `brandkit` | Premium brand-kit image generation skill for creating high-end brand-guidelines boards, logo systems, identity decks, and visual-world presentations. Trained for minimalist, cinematic, editorial, dar… |
| `design-taste-frontend` | Anti-slop frontend skill for landing pages, portfolios, and redesigns. The agent reads the brief, infers the right design direction, and ships interfaces that do not look templated. Real design syste… |
| `design-taste-frontend-v1` | The original v1 taste-skill, preserved for projects depending on its exact behavior. The current default is `design-taste-frontend` (v2 experimental), which is a substantial rewrite. Use this v1 inst… |
| `full-output-enforcement` | Overrides default LLM truncation behavior. Enforces complete code generation, bans placeholder patterns, and handles token-limit splits cleanly. Apply to any task requiring exhaustive, unabridged out… |
| `gpt-taste` | Elite UX/UI & Advanced GSAP Motion Engineer. Enforces Python-driven true randomization for layout variance, strict AIDA page structure, wide editorial typography (bans 6-line wraps), gapless bento gr… |
| `high-end-visual-design` | Teaches the AI to design like a high-end agency. Defines the exact fonts, spacing, shadows, card structures, and animations that make a website feel expensive. Blocks all the common defaults that mak… |
| `image-to-code` | Elite website image-to-code skill for Codex. For visually important web tasks, it must first generate the design image(s) itself, deeply analyze them, then implement the website to match them as clos… |
| `imagegen-frontend-mobile` | Elite mobile app image-generation skill for creating premium, app-native screen concepts and flows. Designed for iOS, Android, and cross-platform mobile products. Prioritizes clean hierarchy, comfort… |
| `imagegen-frontend-web` | Elite frontend image-direction skill for generating premium, conversion-aware website design references. CRITICAL OUTPUT RULE — generate ONE separate horizontal image FOR EVERY section. A landing pag… |
| `industrial-brutalist-ui` | Raw mechanical interfaces fusing Swiss typographic print with military terminal aesthetics. Rigid grids, extreme type scale contrast, utilitarian color, analog degradation effects. For data-heavy das… |
| `minimalist-ui` | Clean editorial-style interfaces. Warm monochrome palette, typographic contrast, flat bento grids, muted pastels. No gradients, no heavy shadows. |
| `redesign-existing-projects` | Upgrades existing websites and apps to premium quality. Audits current design, identifies generic AI patterns, and applies high-end design standards without breaking functionality. Works with any CSS… |
| `stitch-design-taste` | Semantic Design System Skill for Google Stitch. Generates agent-friendly DESIGN.md files that enforce premium, anti-generic UI standards — strict typography, calibrated color, asymmetric layouts, per… |

### external/qiushi-skill(10)

| 技能 | 描述(模型看不到) |
|---|---|
| `arming-thought` | \| 触发：在每次新的顶层对话开始时自动调用，用于建立“实事求是”的总原则，并在明确适用时为后续任务选择下游 skill；如果你是被派遣执行单一具体任务的子 agent，则跳过此 skill。 English: Trigger at the start of each new top-level conversation to establish the core methodology and … |
| `concentrate-forces` | \| 触发：当多个任务同时争夺时间、注意力、算力或预算，必须确定主攻方向并停止分散用力时调用；常见信号包括优先级过多、资源紧张、推进分散、需要决定先做什么。 English: Trigger when limited resources are being split across too many tasks and one main target must be chosen. Use thi… |
| `criticism-self-criticism` | \| 触发：当一项工作已经完成、进入阶段验收、收到批评反馈，或反复出现同类错误需要系统纠偏时调用；常见信号包括 review、audit、retrospective、quality check、纠错与复盘。 English: Trigger after delivery or at a review checkpoint when quality must be examined honestly… |
| `investigation-first` | \| 触发：当你准备下判断、做决策或提出建议，但事实、上下文或一手信息还不充分时优先调用；常见信号包括 unknowns、信息缺口、证据不足、领域陌生、需要先摸清现状。 English: Trigger before making claims or decisions when context is incomplete, evidence is weak, or the domain is u… |
| `mass-line` | \| 触发：当你需要收集多方意见、把零散反馈整合成可执行方案，或把方案带回真实使用者/执行者验证时调用；常见信号包括 stakeholder input、user feedback、意见汇总、对齐与验证。 English: Trigger when input must be gathered from many people, synthesized into a clearer plan, a… |
| `overall-planning` | \| 触发：当你需要在多个目标、利益方或相互制约的指标之间做动态平衡时调用；常见信号包括 trade-offs、目标冲突、系统性约束、优化一项会伤害另一项。 English: Trigger when several important goals must be advanced together and optimizing one dimension can damage another. … |
| `practice-cognition` | \| 触发：当你提出了方案、假设或判断，需要通过实践验证、试错迭代或复盘升级认知时调用；常见信号包括 experiment、prototype、validate、iterate、feedback loop。 English: Trigger when an idea, hypothesis, or plan must be tested in practice and improved throu… |
| `protracted-strategy` | \| 触发：当目标长期、任务复杂、资源暂时处于劣势，或短期无法速胜但又不能放弃时调用；常见信号包括 long-term effort、phased plan、endurance、战略耐心、需要分阶段推进。 English: Trigger when the work is long-horizon, difficult, and unlikely to be won quickly. Use th… |
| `spark-prairie-fire` | \| 触发：当你从零起步、资源极少、需要先找到最小可行切入口并建立稳定根据地时调用；常见信号包括 bootstrap、MVP、pilot、first foothold、小团队起步。 English: Trigger when starting from almost nothing and needing a viable foothold before scaling up. Use this … |
| `workflows` | \| 触发：当你面临的任务明显需要多个思想武器协作时调用；常见信号包括：从零启动新项目、攻坚复杂疑难问题、对已有方案进行迭代优化。此 skill 提供标准化的跨 skill 工作流组合，解决"应该先用哪个 skill、怎么衔接"的问题。 English: Trigger when a task clearly requires multiple skills in sequence. Use th… |

### external/caveman(6)

| 技能 | 描述(模型看不到) |
|---|---|
| `cavecrew` | > Decision guide for delegating to caveman-style subagents. Tells the main thread WHEN to spawn `cavecrew-investigator` (locate code), `cavecrew-builder` (1-2 file edit), or `cavecrew-reviewer` (diff… |
| `caveman-commit` | > Ultra-compressed commit message generator. Cuts noise from commit messages while preserving intent and reasoning. Conventional Commits format. Subject ≤50 chars, body only when "why" isn't obvious.… |
| `caveman-compress` | > Compress natural language memory files (CLAUDE.md, todos, preferences) into caveman format to save input tokens. Preserves all technical substance, code, URLs, and structure. Compressed version ove… |
| `caveman-help` | > Quick-reference card for all caveman modes, skills, and commands. One-shot display, not a persistent mode. Trigger: /caveman-help, "caveman help", "what caveman commands", "how do I use caveman". |
| `caveman-review` | > Ultra-compressed code review comments. Cuts noise from PR feedback while preserving the actionable signal. Each comment is one line: location, problem, fix. Use when user says "review this PR", "co… |
| `caveman-stats` | > Show real token usage and estimated savings for the current session. Reads directly from the Claude Code session log — no AI estimation. Triggers on /caveman-stats. Output is injected by the mode-t… |

### external/loopy(2)

| 技能 | 描述(模型看不到) |
|---|---|
| `loop-library` | Compatibility alias for Loopy. Use only when an existing installation or older instruction explicitly invokes loop-library; use Loopy for new installations and requests. Provides the same discovery, … |
| `loopy` | Discover, find, compare, audit, repair, adapt, craft, run, debrief, and prepare repeatable AI-agent loops for publication. Use when a user asks to analyze code or coding threads for recurring work, f… |

### external/yes.md(2)

| 技能 | 描述(模型看不到) |
|---|---|
| `yes-ja` | "ファイル・設定・データベース・デプロイの変更を伴うタスクで発動。デバッグが2回以上連続で失敗した時に発動。証拠なしに推測・仮定しようとした時に発動（「おそらく」「多分」「〜だと思う」「〜のはず」）。ユーザーに丸投げしようとした時に発動（「ご確認ください」「手動で対応してください」「〜が必要かもしれません」）。修正後に動作確認せず完了と報告しようとした時に発動。根本原因の結論を出す時に発動。使え… |
| `yes-zh` | "當任務涉及修改檔案、設定、資料庫或部署時觸發。當除錯連續失敗 2 次以上時觸發。當即將猜測或假設而沒有證據時觸發（「應該是」「可能是」「我覺得」「感覺是」）。當把問題推給用戶時觸發（「請你檢查」「建議您手動」「你可能需要」）。當改完東西沒有驗證就說完成時觸發。當下結論或判定根因時觸發。當有工具卻不用時觸發（有 WebSearch 不搜、有 Bash 不跑、有 Read 不讀）。當原地打轉時觸發… |

### external/Local-Agent-Workspace(1)

| 技能 | 描述(模型看不到) |
|---|---|
| `case-framework` | Enforce or bootstrap the Context-Aware Scaffold Engine (C.A.S.E.) protocol, a file-as-state dual-track agent workflow. Make sure to use this skill whenever the user mentions code quality, task pipeli… |

### external/evolver(1)

| 技能 | 描述(模型看不到) |
|---|---|
| `capability-evolver` | A self-evolution engine for AI agents. Analyzes runtime history to identify improvements and applies protocol-constrained evolution. Communicates with EvoMap Hub via local Proxy mailbox. |

### external/karpathy-skills(1)

| 技能 | 描述(模型看不到) |
|---|---|
| `karpathy-guidelines` | Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiab… |

### external/llm-wiki-plugin(1)

| 技能 | 描述(模型看不到) |
|---|---|
| `llm-wiki` | \| Build and maintain an LLM-curated personal knowledge base — the "LLM Wiki" pattern from Andrej Karpathy's April 2026 gist. Use this skill whenever the user wants to ingest a source (paper, article,… |

### external/planning-with-files(1)

| 技能 | 描述(模型看不到) |
|---|---|
| `pi-planning-with-files` | Implements Manus-style file-based planning to organize and track progress on complex tasks. Creates task_plan.md, findings.md, and progress.md. Use when asked to plan out, break down, or organize a m… |

### external/prompt-master(1)

| 技能 | 描述(模型看不到) |
|---|---|
| `prompt-master` | Generates optimized prompts for AI tools. Activates only when the user explicitly asks to write, fix, improve, or adapt a prompt for a specific AI tool (LLM, Cursor, Midjourney, image AI, video AI, c… |

## 重新產生

```bash
PI_HARNESS_DUMP_PROMPT=/tmp/p.txt pi --print "hi"
python scripts/audit-skill-reach.py --prompt /tmp/p.txt --out docs/measurements/skill-reachability.md
```

沒有 `--prompt` 時 core 層從 `external-skills-manifest.json` 讀,
**那份清單不含外來技能**,寫這份文件時它漏掉了 43 個裡的 19 個。
