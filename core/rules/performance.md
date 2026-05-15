# Performance Optimization

## Model Selection Strategy

**Haiku 4.5** (90% of Sonnet capability, 3x cost savings):
- Lightweight agents with frequent invocation
- Pair programming and code generation
- Worker agents in multi-agent systems

**Sonnet 4.6** (Best coding model):
- Main development work
- Orchestrating multi-agent workflows
- Complex coding tasks

**Opus 4.5** (Deepest reasoning):
- Complex architectural decisions
- Maximum reasoning requirements
- Research and analysis tasks

## Context Window Management

Avoid last 20% of context window for:
- Large-scale refactoring
- Feature implementation spanning multiple files
- Debugging complex interactions

Lower context sensitivity tasks:
- Single-file edits
- Independent utility creation
- Documentation updates
- Simple bug fixes

## Extended Thinking + Plan Mode

Extended thinking is enabled by default, reserving up to 31,999 tokens for internal reasoning.

Control extended thinking via:
- **Toggle**: Option+T (macOS) / Alt+T (Windows/Linux)
- **Config**: Set `alwaysThinkingEnabled` in `~/.claude/settings.json`
- **Budget cap**: `export MAX_THINKING_TOKENS=10000`
- **Verbose mode**: Ctrl+O to see thinking output

For complex tasks requiring deep reasoning:
1. Ensure extended thinking is enabled (on by default)
2. Enable **Plan Mode** for structured approach
3. Use multiple critique rounds for thorough analysis
4. Use split role sub-agents for diverse perspectives

## Build Troubleshooting

If build fails:
1. Use **build-error-resolver** agent
2. Analyze error messages
3. Fix incrementally
4. Verify after each fix

---

## 🧠 上下文內核協議 (Context Engineering Kernel)
*此規則集源自 Context Engineering 蒸餾，旨在優化長對話下的注意力預算，為本專案的底層被動技能。*

1.  **Prefix-Stabilization (KV-Cache 穩定化)**:
    - 始終將穩定的指令（System Prompt, Rules）放在 Prompt 最前端。
    - 動態元數據（日期、Session ID）必須放在穩定前綴之後，嚴禁插入前綴中間。
2.  **U-Curve Placement (注意力 U 型分配)**:
    - 關鍵任務目標 (Goals) 與最終驗證標準 (Verification) 必須放置在 Context Window 的最開頭與最末尾。
    - 中間區域為「資訊陷阱」，僅限放置支持性數據或詳細日誌。
3.  **Observation Masking (觀察值掩碼)**:
    - 工具輸出 (Tool Outputs) 佔用 80% 的 Token。
    - 一旦對某個輸出完成總結或做出決策，後續對話應將原始 Raw Output 替換為簡短引用：`[Obs elided. Key findings: X, Y, Z]`。
4.  **BDI Mental Mapping (心理狀態映射)**:
    - 維持內部的 **Beliefs** (經工具驗證的事實)、**Desires** (用戶最終目標) 與 **Intentions** (下一步原子操作) 狀態。
    - 每輪回覆前，必須根據外部 `task_plan.md` 同步此內部狀態。

*(Ref: upstream/Agent-Skills-for-Context-Engineering)*

