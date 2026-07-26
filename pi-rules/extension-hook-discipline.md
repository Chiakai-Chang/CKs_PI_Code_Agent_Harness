# Extension Hook Discipline

This file governs how harness bridges use Pi's ExtensionAPI event system. It is
mandatory policy for any bridge operating in this repo. If a Pi upstream hook
behavior change conflicts with this file, **this file's principles win** — the
bridge must adapt to keep the principle, not drop it.

## Composition rules

1. **System prompt append only.** `before_agent_start` handlers may append to
   `event.systemPrompt` but must never replace another extension's prompt.
   Return `{ systemPrompt: (event.systemPrompt ?? "") + "\n\n" + addition }`.
2. **Uninvolved handlers return undefined.** A hook handler that has nothing to
   do for the current event returns `undefined` — never mutate state or send
   messages on unrelated events.
3. **Hook choice is documented.** Every bridge's RATIONALE.md (or its source
   header) states which hooks it uses and why, plus which hooks it intentionally
   does not use and why (e.g. "session_before_compact not used — mutation before
   compaction is ineffective per Pi engine behavior").
4. **No session control from event handlers.** `ctx.newSession()`, `ctx.fork()`,
   and `ctx.reload()` are only available in command handlers — calling them from
   an event handler deadlocks silently (Pi just hangs). This distinction between
   `ExtensionContext` (events) and `ExtensionCommandContext` (commands) is the
   single most important thing to understand before writing non-trivial hooks.

## Hook selection reference

| Hook | Use for | Do NOT use for |
|---|---|---|
| `session_start` | Detect project state, register status, one-time setup | Per-turn prompt injection |
| `before_agent_start` | Append context/discipline to system prompt each turn | Replacing system prompt; session control |
| `tool_call` | Intercept/block tool execution (with `{block:true}`) | Post-execution transformation |
| `tool_result` | Transform/filter tool output before model sees it | Pre-execution blocking |
| `agent_settled` | Own automatic continuation decisions after a turn | Queueing work on session end |
| `turn_end` | Non-blocking background work (check scripts, telemetry) | Anything that must complete before next turn |
| `session_compact` | Schedule post-compaction re-anchoring (hidden entry on next turn) | Pre-compaction prompt mutation (ineffective) |
| `resources_discover` | Register skills/tools at session start/reload | Per-turn behavior |

## Known traps

- **`session_before_compact` is ineffective for prompt mutation.** Pi's compaction
  may discard pre-compact prompt changes. Use `session_compact` to schedule a
  hidden `CustomMessageEntry` re-anchor on the next turn instead.
- **`agent_end` vs `agent_settled`.** `agent_end` fires on session end (including
  user leaving); it is not the right hook for automatic continuation. Use
  `agent_settled` — it fires after each agent turn settles, while the session
  is still alive.
- **Double-up on overflow compaction.** Pi's overflow recovery already retries
  the aborted turn itself (`event.willRetry === true`). Sending a continuation
  on top races/queues two turns. Check `willRetry` first.

## Sources

Pi extension documentation: <https://pi.dev/docs/latest/extensions>
Practical lifecycle guide: nunorralves.pt/posts/2026-06-08-pi-extensions
Reference implementation hook contract: pi-until-done README "Runtime contract"
