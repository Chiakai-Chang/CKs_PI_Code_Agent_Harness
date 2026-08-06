# C.A.S.E. Framework — Project Rules

> This project uses the C.A.S.E. (Constitution-Architecture-State-Execution) framework.
> All AI agents MUST read and follow the rules below.

## Directory Structure
```
00_Constitution/    — READ-ONLY: Global constraints (core.md)
01_Roadmap/         — READ-ONLY: Phase plan (roadmap.md, global_dod.md)
02_Task_Queue/      — READ-WRITE: Agent workspace (task folders)
```

## Agent Operating Rules
1. **Read MAP.md first** — it is your navigation index
2. **Obey the Constitution** — never modify `00_Constitution/` or `01_Roadmap/`
3. **Stay in your lane** — only read/write your assigned task folder
4. **File-as-State** — all progress lives in files, not conversation context
5. **Dual-track verification** — Worker and Checker roles must be separate
6. **Git small steps** — commit after every meaningful change
7. **3-strike self-healing** — max 3 attempts before escalating

## Status Machine
`PENDING` → `IN_PROGRESS` → `REVIEW` → `DONE`
`IN_PROGRESS` → `ESCALATED` (on persistent failure)

## For Humans
To redeploy or update the navigation indices, run:
```bash
python scripts/bootstrap.py .
```
To verify a task folder's C.A.S.E. compliance:
```bash
# Using Python:
python .agents/skills/case-framework/verifiers/verify.py 02_Task_Queue/Task_<NNN>_<slug>

# Using Node.js:
node .agents/skills/case-framework/verifiers/verify.js 02_Task_Queue/Task_<NNN>_<slug>
```
Then instruct your AI agent: "This project uses C.A.S.E. framework. Read CASE.md."
