/**
 * Safety Hooks Bridge Extension (folder: yes-hooks-bridge)
 *
 * Hosts deterministic guards the model CANNOT ignore — the whole point of a
 * hook over a text rule, and especially valuable with weak/uncensored local
 * models that drift past AGENTS.md prose under load:
 *
 *   1. Destructive-command guard — wires YES.md's `pre-bash-guard.sh` to block
 *      `rm -rf /`, `git push --force`, `DROP TABLE`, `mkfs`, fork bombs, … on the
 *      `bash` tool. Scope deliberately narrow (MECE): only the destructive
 *      blocker; YES.md's post-edit / post-deploy reminders duplicate AGENTS.md §9
 *      and are intentionally skipped. The behavioral-discipline half of YES.md
 *      ships as the `yes` skill, not here.
 *
 *   2. Directory-containment guard — blocks `write`/`edit` whose resolved target
 *      escapes the session cwd (the project root Pi was launched in). Fixes the
 *      observed "資料夾亂跳" failure: a run in one project wrote files into a
 *      sibling project AND edited this harness's own scripts. Relative paths
 *      resolve under cwd (allowed); absolute or `../` paths that leave cwd are
 *      blocked. Fails open if cwd/path can't be resolved.
 *
 *   2b. Vendored-submodule guard — blocks `write`/`edit` into `external/*`.
 *      Containment allows it (submodules sit inside the project root) and that
 *      is exactly wrong here: asked to load a skill, the model once wrote its
 *      own invented content over a genuine upstream SKILL.md.
 *
 *   3. Loop guard — on `turn_end`, catches a turn that made no real tool call
 *      but whose text is shaped like one (`<invoke>`, `<read-files>`, `<bash>
 *      <command>`, …). These never execute; a weak model can echo the shape
 *      from Pi's own compaction-summary format (which legitimately ends with
 *      `<read-files>`/`<modified-files>` tags) and then loop on its own echo.
 *      After 3 consecutive strikes, queues a corrective message for the next
 *      turn — AGENTS.md §4's "3-Strike Cap", enforced as code.
 *
 *   4. Runaway-argument guard — blocks a REAL tool call whose argument value
 *      carries tool-call syntax or is absurdly long. Observed: a genuine
 *      `web_search` whose `query` grew to 145,638 chars of looping XML until the
 *      output cap. Invisible to guard 3 (there IS a call) and to the markup
 *      scan (it never inspects argument values).
 *
 *   5. Repeat-call guard — blocks an identical call repeated past a limit.
 *      Captured live: the same `read` 26 times while context grew to 51,915.
 *
 *   6. Fabricated-work guard — a turn that ends normally, calls nothing, and
 *      either denies having filesystem access (with `read` in the tool list) or
 *      claims work it never did. Carries no markup, so guard 3 cannot see it.
 *
 *   7. Unfulfilled-intent guard — a turn that ANNOUNCES its next step and then
 *      ends ("Check existence:", "Write failing test first."). The semantic
 *      opposite of guard 6, which matches claims of COMPLETED work. Found in the
 *      2026-07-30 real-session validation: five occurrences across six sessions,
 *      three of them inside deep-research children, and three of six tasks
 *      produced nothing because of it.
 *
 *   8. Cross-shell quoting guard — blocks `powershell -Command "…$var…"` issued
 *      through the bash tool, where bash expands the variables before PowerShell
 *      ever starts. Same validation round: three turns lost to a command that
 *      was valid PowerShell and could never work.
 *
 * Guards 4-8 all share one property: every existing guard was blind to them.
 * That is the test for whether a new guard is worth its weight here.
 */
import type { ExtensionAPI, ToolCallEvent, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { readFileSync, existsSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, resolve, relative, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";
import { homedir } from "node:os";
import { spawnSync } from "node:child_process";
import { CycleDetector, SAME_QUERY_LIMIT } from "./loop-detect.ts";
import { ResearchDepthGuard } from "./research-depth.ts";
import { bashContainmentBlock } from "./bash-containment.ts";
import { BlockedClaimTracker } from "./blocked-claim.ts";
import { containmentRefusal, workspaceListing } from "./harness-root.ts";
import { compactionEcho } from "./compaction-echo.ts";
import { scrubToolInput, type ResidueRemoval } from "./dialect-residue.ts";

function harnessRoot(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  try {
    const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf-8"));
    if (pkg["pi-harness"]?.root) return pkg["pi-harness"].root;
  } catch {}
  return join(here, "../..");
}

function guardScript(): string {
  return join(harnessRoot(), "external/yes.md/hooks/pre-bash-guard.sh");
}

// ---------------------------------------------------------------------------
// Dialect residue: repaired for the model, reported to the operator.
//
// The removals go to `ctx.ui.notify` and to a file, and to nothing else. The
// model is the wrong audience — it cannot change its own chat template, so a
// message about the residue can only cost it a turn, and the GateGuard
// misdelivery in this same session shows what a misread notice does to the next
// action. The operator can fix it, with a server restart that
// `scripts/check-model-serving.py` names.
//
// Notified once per session, not per call. The measured session would have
// produced 24 of these, which is the same failure as the learning-point notice
// that repeated 122 times and meant nothing by the third.
// ---------------------------------------------------------------------------
let residueTotal = 0;
let residueAnnounced = false;
const residueSeen: ResidueRemoval[] = [];

function residueReportPath(): string {
  return join(harnessRoot(), "pi-config", "serving-mismatch-report.json");
}

function recordResidue(removed: ResidueRemoval[], ctx: ExtensionContext): void {
  if (!removed.length) return;
  residueTotal += removed.length;
  // Bounded: a report is evidence, not a log. The shape repeats after the first
  // few and the count is what matters.
  for (const r of removed) if (residueSeen.length < 50) residueSeen.push(r);

  if (!residueAnnounced) {
    residueAnnounced = true;
    const first = removed[0];
    ctx.ui.notify(
      `🧩 Tool arguments carried '${first.tag}' from the model's chat template ` +
        `(in ${first.tool}.${first.field}). Removed before the call ran. The ` +
        `served template teaches a tool-call dialect this harness does not use — ` +
        `run: python scripts/check-model-serving.py`,
      "warning",
    );
  }

  try {
    writeFileSync(
      residueReportPath(),
      JSON.stringify(
        {
          version: 1,
          generatedAt: new Date().toISOString(),
          note:
            "Tool-call dialect residue removed from tool arguments before " +
            "execution. Cause is the served chat template, not the model and " +
            "not this harness; see scripts/check-model-serving.py.",
          removedTotal: residueTotal,
          samples: residueSeen,
        },
        null,
        2,
      ),
      "utf-8",
    );
  } catch {
    // A report that cannot be written must not take the session with it. The
    // repair already happened; this is the record of it.
  }
}

// Resolve a real shell (Node's bare "sh" ENOENTs on Windows — see stealth-web).
function findShell(): string {
  try {
    const cfg = JSON.parse(readFileSync(join(homedir(), ".pi", "agent", "settings.json"), "utf-8"));
    if (cfg.shellPath && existsSync(cfg.shellPath)) return cfg.shellPath;
  } catch {}
  for (const c of [
    "C:\\Program Files\\Git\\bin\\bash.exe",
    "C:\\Program Files\\Git\\usr\\bin\\bash.exe",
    "C:\\Program Files (x86)\\Git\\bin\\bash.exe",
  ]) {
    try { if (existsSync(c)) return c; } catch {}
  }
  return process.platform === "win32" ? "bash" : "sh";
}

// Guard 1: destructive shell commands, via YES.md pre-bash-guard.sh.
function bashGuard(event: ToolCallEvent, ctx: ExtensionContext) {
  const cmd = (event.input as { command?: unknown })?.command;
  if (typeof cmd !== "string" || !cmd) return;
  const script = guardScript();
  if (!existsSync(script)) return; // yes.md submodule absent — fail open, don't break bash
  let r;
  try {
    r = spawnSync(findShell(), [script, cmd], { timeout: 4000, encoding: "utf-8" });
  } catch {
    return; // guard itself failed — fail open rather than block legit work
  }
  if (r.status === 1) {
    const matched = (r.stdout || "")
      .split("\n")
      .map((l) => l.trim())
      .find((l) => l.startsWith("Matched:")) || "destructive pattern";
    ctx.ui.notify(`🚨 YES.md blocked a destructive command (${matched})`, "error");
    return {
      block: true,
      reason: `YES.md pre-bash-guard blocked a destructive command (${matched}). If you truly need it, ask the user to run it.`,
    };
  }
}

// Guard 8: a PowerShell one-liner whose variables bash will eat first.
//
// Pi runs commands through bash even on Windows. Observed 2026-07-30, three
// turns in a row, right after another guard had un-stalled the session:
//
//     powershell -Command "& { $bats = Get-ChildItem ...; foreach ($b in $bats) ... }"
//
// bash expands $bats and $b to nothing before PowerShell is started, and
// PowerShell answers "foreach 後面應該是變數名稱". The model cannot see why —
// the command it wrote is valid PowerShell — so it rewrites it and fails again.
// The task never finished.
//
// Only double quotes are affected: bash does not interpolate inside single
// quotes, and `\$` survives intact. Both stay allowed, because they are the
// correct way to write this and a guard that blocks the correct form is worse
// than the bug. Checking at tool_call costs nothing per turn, unlike a prompt
// rule, and lets the message name the fix rather than leaving the model to guess.
const POWERSHELL_DOUBLE_QUOTED_VAR =
  /\b(?:powershell(?:\.exe)?|pwsh(?:\.exe)?)\b[^\n]*?-(?:Command|c)\b[^\n]*?"[^"]*(?<!\\)\$/i;

function crossShellQuotingGuard(event: ToolCallEvent, ctx: ExtensionContext) {
  const cmd = (event.input as { command?: unknown })?.command;
  if (typeof cmd !== "string" || !cmd) return;
  if (!POWERSHELL_DOUBLE_QUOTED_VAR.test(cmd)) return;
  ctx.ui.notify("🚨 Blocked a PowerShell command whose $variables bash would expand first", "error");
  return {
    block: true,
    reason:
      "這個指令會先經過 bash，雙引號裡的 $variable 會在 PowerShell 收到之前就被展開成空字串"
      + "（實測症狀：PowerShell 回報 `foreach 後面應該是變數名稱`）。改用下列任一種："
      + "\n  1. 單引號：powershell -Command '...$x...'"
      + "\n  2. 把腳本寫成 .ps1 檔再執行"
      + "\n  3. 直接用 bash 原生指令（ls / find / grep）完成同一件事",
  };
}

// Guard 2: keep write/edit inside the session cwd (the project Pi was launched in).
// Mirrors Pi's own resolveToCwd: relative paths resolve under cwd; absolute paths
// stay absolute. A target that escapes cwd (sibling project, this harness, home) is
// blocked so a drifting model can't scatter files across the disk.
// Guard 2b: writes into a vendored git submodule.
//
// Observed for real: asked to load a skill, the model took the path out of
// skill-catalog.json and, instead of reading it, `write`-d its own invented
// content over external/ecc/skills/agent-architecture-audit/SKILL.md —
// destroying the genuine upstream skill. The containment guard let it through
// because external/ is inside the project root, which is exactly right for
// containment and exactly wrong here: submodule contents are vendored, they
// belong to another repository, and an edit there is silently lost on the next
// `git submodule update` even when it is not a hallucination.
//
// Reads are untouched. `bash` is not covered — a human deliberately
// contributing upstream still can, via git — so this blocks the accident
// without blocking the intent.
function submoduleRoots(cwd: string): string[] {
  try {
    const gitmodules = readFileSync(join(cwd, ".gitmodules"), "utf-8");
    return [...gitmodules.matchAll(/^\s*path\s*=\s*(.+?)\s*$/gm)].map((m) => m[1].replace(/\\/g, "/"));
  } catch {
    return [];
  }
}

function vendoredGuard(
  event: ToolCallEvent,
  ctx: ExtensionContext,
  cwd: string,
  target: string,
  rel: string,
) {
  const relPosix = rel.replace(/\\/g, "/");
  const hit = submoduleRoots(cwd).find((p) => relPosix === p || relPosix.startsWith(p + "/"));
  if (!hit) return;
  ctx.ui.notify(`🚨 Blocked ${event.toolName} into vendored submodule ${hit}: ${target}`, "error");
  return {
    block: true,
    reason:
      `Vendored submodule: "${target}" lives inside the git submodule "${hit}", which is another ` +
      `repository's content. Writing there overwrites upstream files and is discarded by the next ` +
      `submodule update. If you meant to READ this file (e.g. to load a skill), use the read tool. ` +
      `If you genuinely need to change upstream code, tell the user rather than editing in place.`,
  };
}

// Guard 4: a native tool call whose ARGUMENTS ran away.
//
// Observed on this machine, and the most damaging failure found all day. The
// model opened a real `web_search` call and then, inside the `query` string,
// began emitting XML-format tool calls and looping on them:
//
//   {"query": "Wikipedia \"Accessibility tree\"</parameter>\n</function>\n
//    </tool_call>\n<tool_call>\n<function>web_search>\n<parameter=query>\n…"}
//
// 145,638 characters of that, until the 32,768-token output cap was hit
// (usage.output = 32768, stopReason = "length"). Pi then refuses the call —
// "the response hit the output token limit, so its arguments may be truncated"
// — and the model simply tries again the same way. Two attempts, ~700 seconds,
// a 297KB session, zero progress.
//
// None of the other guards see this: it IS a native tool call, so the loop
// guard's "no real tool call" test never fires, and the garbage lives inside
// the arguments, which FAKE_TOOL_CALL_PATTERN (a message-text scan) never
// inspects.
//
// Blocking costs nothing — Pi was going to reject the call anyway — but it
// replaces a confusing engine message with a specific instruction, which is the
// difference between the model repeating the failure and correcting it.
//
// The optional namespace prefix carries the same fix as FAKE_TOOL_CALL_PATTERN:
// `</atem:parameter>` did not match `<\/?parameter\b`, so on session 019ffbdd
// this guard saw 24 corrupted arguments and stayed silent. write/edit are
// repaired before this runs (see dialect-residue.ts) precisely so this guard
// keeps the cases it judges better — a leak in a `command` or a `query` is a
// generation runaway the model can fix, and refusing it says so.
const ARG_SYNTAX_LEAK = /<\/?(?:[A-Za-z][\w.-]*:)?(?:tool_call|function|parameter|function_calls|invoke)\b|<\|tool▁call/i;
const MAX_ARG_CHARS = 8000;

function runawayArgumentGuard(event: ToolCallEvent, ctx: ExtensionContext) {
  let serialized: string;
  try {
    serialized = JSON.stringify(event.input ?? {});
  } catch {
    return; // unserializable input — not our business, fail open
  }
  const leaked = ARG_SYNTAX_LEAK.test(serialized);
  const oversized = serialized.length > MAX_ARG_CHARS;
  if (!leaked && !oversized) return;

  // An oversized `content`/`command` is legitimate — writing a big file, running
  // a long script. Only the syntax leak is unambiguous on its own; size alone
  // is judged on fields that should never be large.
  if (!leaked) {
    const input = (event.input ?? {}) as Record<string, unknown>;
    const bulkFields = ["content", "command", "newText", "text"];
    const nonBulk = Object.entries(input)
      .filter(([k]) => !bulkFields.includes(k))
      .reduce((n, [, v]) => n + (typeof v === "string" ? v.length : 0), 0);
    if (nonBulk <= MAX_ARG_CHARS) return;
  }

  ctx.ui.notify(
    `🚨 ${event.toolName} arguments ran away (${serialized.length} chars${leaked ? ", tool-call syntax leaked into a value" : ""})`,
    "error",
  );
  return {
    block: true,
    reason:
      `Your ${event.toolName} arguments are malformed: ${serialized.length} characters` +
      (leaked ? `, and a value contains raw tool-call syntax (</parameter>, </tool_call>, <function>).` : ".") +
      ` You started a tool call and then kept generating instead of stopping at its end. ` +
      `Emit ONE call with short, plain arguments — for a search, the query is a few words — and ` +
      `stop generating immediately after it. Do not put tool-call markup inside an argument value.`,
  };
}

// Guard 5: the same call, over and over, each one succeeding.
//
// Captured live (session 019fab1e): 26 consecutive
// `read {"path":"scripts/verify-bridges.py"}` calls in answer to a one-line
// prompt, each returning the same file, prompt growing ~1,464 tokens per turn
// to 51,915 before the 10-minute cap killed it.
//
// No existing guard could see it. The loop guard keys on "turn ended with NO
// real tool call" and every one of these turns had one, so its counters reset
// each time. runawayArgumentGuard looks for oversized or markup-bearing
// argument values; these arguments were short and correct. A call that
// succeeds and teaches the model nothing is a blind spot for both.
//
// Consecutive only: any different call resets the count, so edit/test/edit/test
// cycles — identical `bash` calls separated by real work — are untouched.
const REPEAT_CALL_LIMIT = 4;
// How many times the speed bump above may fire for the SAME call before it
// becomes a brake. Captured live 2026-07-31 on the task "Reply with exactly:
// OK": 76 turns, 130 identical `web_search{"query":"OK"}` calls, ~70 minutes.
// The guard fired 18 times and said the right thing every time — and the
// session never stopped, because hitting the limit resets the counter and hands
// the model a fresh budget. That reset is deliberate and stays; blocking every
// subsequent call forever trades one loop for another. What was missing is a
// count that SURVIVES the reset.
const REPEAT_OFFENCE_LIMIT = 3;
let lastCallSignature = "";
let repeatedCallCount = 0;
let repeatOffences = 0;
let repeatBreakerTripped = false;

// Cycling loops are per session, like every other counter here.
const cycleDetector = new CycleDetector();

// Guard 10 — see research-depth.ts. Separate object from the cycle detector
// because they answer different questions: that one asks "have I asked this
// before?", this one asks "have I read anything, and have I written anything
// down?". The measured session that motivated it repeated no query at all.
const researchDepth = new ResearchDepthGuard();

// Guard 11 — see blocked-claim.ts. A guard doing its job produces a session
// record that says the opposite when the reply claims the refused change
// happened; watched live twice on 2026-08-06.
const blockedClaims = new BlockedClaimTracker();

// Files the current turn wrote. A reply that substitutes a summary for the
// answer usually has the answer on disk already, and naming it beats asking for
// the work a second time. Module scope, like the guards above: Pi calls the
// default export once per process, and this is cleared at every turn_end.
let turnWrites: string[] = [];

function repeatCallGuard(event: ToolCallEvent, ctx: ExtensionContext, pi: ExtensionAPI) {
  let signature: string;
  try {
    signature = `${event.toolName}:${JSON.stringify(event.input ?? {})}`;
  } catch {
    return; // unserializable input — can't fingerprint, fail open
  }
  if (signature !== lastCallSignature) {
    // A different call means the model took the advice. Clear everything,
    // including the breaker: it exists to stop one loop, not to punish a model
    // that moved on.
    lastCallSignature = signature;
    repeatedCallCount = 1;
    repeatOffences = 0;
    repeatBreakerTripped = false;
    return;
  }
  repeatedCallCount += 1;

  if (repeatBreakerTripped) {
    return {
      block: true,
      reason:
        `Repeat-call guard: this identical \`${event.toolName}\` call has now been refused ` +
        `${REPEAT_OFFENCE_LIMIT} separate times and is blocked for good. Stop calling it. ` +
        `Say in plain text what you were trying to find out and what is blocking you.`,
    };
  }

  if (repeatedCallCount < REPEAT_CALL_LIMIT) return;

  repeatOffences += 1;
  // Reset so the model gets a fresh budget after being told; blocking every
  // subsequent call would trade one loop for another.
  repeatedCallCount = 0;

  if (repeatOffences >= REPEAT_OFFENCE_LIMIT) {
    repeatBreakerTripped = true;
    ctx.ui.notify(
      `🛑 Repeat-call breaker: '${event.toolName}' looped ${REPEAT_OFFENCE_LIMIT}× despite corrections — handing back to you.`,
      "error",
    );
    pi.sendMessage(
      {
        customType: "loop-guard",
        content:
          `[SYSTEM] 你對 \`${event.toolName}\` 發出了完全相同的呼叫、被糾正 ${REPEAT_OFFENCE_LIMIT} 次仍在重複。` +
          `這一輪到此為止，控制權交還使用者。請用純文字說明你想查什麼、卡在哪裡。`,
        display: true,
      },
      // "nextTurn", NOT "followUp"+triggerTurn: re-triggering a loop is fuel.
      // This queues for the next human prompt, which is exactly the stop that
      // was missing — the observed loop ran 70 minutes with nothing to end it.
      { deliverAs: "nextTurn" },
    );
    return {
      block: true,
      reason:
        `Repeat-call guard: ${REPEAT_OFFENCE_LIMIT} rounds of the identical \`${event.toolName}\` call. ` +
        `Stopping and handing back to the user. Do not call it again.`,
    };
  }

  return {
    block: true,
    reason:
      `Repeat-call guard: this is call ${REPEAT_CALL_LIMIT} of an identical ` +
      `\`${event.toolName}\` with identical arguments, with nothing in between. ` +
      `You already have this result in the conversation — scroll up and use it. ` +
      `If the result was not what you needed, change the arguments or use a different tool; ` +
      `if you are stuck, say so in plain text instead of calling again.`,
  };
}

/**
 * Refusals this session, so the second one can stop describing and start
 * showing. Reset at session_start alongside the other per-session state.
 */
let containmentRefusals = 0;

/**
 * Append the workspace listing once this guard has already said its piece.
 *
 * One counter for both containment paths — write/edit and bash — because the
 * model does not care which of our functions refused it, only how many times it
 * has been told the same thing.
 */
function withWorkspaceListing(reason: string, cwd: string): string {
  const seen = containmentRefusals++;
  if (seen < 1 || !cwd) return reason;
  let shown: string | null = null;
  try {
    shown = workspaceListing(cwd, (d) => readdirSync(d),
      (p) => { try { return statSync(p).isDirectory(); } catch { return false; } });
  } catch {
    shown = null;
  }
  return shown
    ? `${reason}

同樣的理由已經擋你第 ${seen + 1} 次了,所以這次不重複講,直接給你看:
${shown}`
    : reason;
}

function containmentGuard(event: ToolCallEvent, ctx: ExtensionContext) {
  const input = event.input as { path?: unknown; file_path?: unknown };
  const raw = typeof input?.path === "string" ? input.path
    : typeof input?.file_path === "string" ? input.file_path : "";
  if (!raw || typeof ctx.cwd !== "string" || !ctx.cwd) return; // can't decide — fail open
  let cwd: string, target: string;
  try {
    cwd = resolve(ctx.cwd);
    target = resolve(cwd, raw); // raw absolute -> unchanged; raw relative -> under cwd
  } catch {
    return; // path math failed — fail open rather than block legit work
  }
  const rel = relative(cwd, target);
  const inside = rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
  if (inside) return vendoredGuard(event, ctx, cwd, target, rel);
  ctx.ui.notify(`🚨 Blocked ${event.toolName} outside project root: ${target}`, "error");
  return {
    block: true,
    // Built by a pure function so a behavioural test can reach it: the refusal
    // supplies the workspace path when the target landed in the harness install
    // — cwd confusion ate two of five measured runs, and the model retried nine
    // times against a refusal that named the mistake and nothing else. Nothing
    // is formatted here, because a string assertion over this file is the only
    // kind available and one of those already let a break through.
    // Both containment paths append the escalation through one function. Having
    // two copies of the idea is what let the bash path ship without it — see
    // withWorkspaceListing.
    reason: withWorkspaceListing(
      containmentRefusal(event.toolName, target, cwd, harnessRoot()), cwd),
  };
}

// Guard 3: catches a turn that ends with NO real tool call but assistant text shaped like
// one (Claude/Superpowers `<read>`, `<write>`, `<edit>`, `<bash>`, `<ls>`, `<dir>`, `<invoke>`, `<tool_code>` tags,
// or Markdown ` ```bash ` code blocks) — text that is never executed. Universal Parser intercepts valid tags and auto-advances.
//
// The `(?:[A-Za-z][\w.-]*:)?` prefix on the tool-call tags is not decoration.
// Until 2026-08-14 this pattern matched `<invoke` and `<parameter name=` and
// therefore did NOT match `<atem:invoke` or `<atem:parameter name=` — the exact
// dialect the local model's chat template was teaching it. A whole tool-call
// syntax walked past this detector, the loop guard and the transformer for a
// 6.5-hour session because of one namespace prefix. Any dialect that namespaces
// its tags would have done the same, so the prefix is optional and general
// rather than a list of the ones seen so far. See dialect-residue.ts.
const FAKE_TOOL_CALL_PATTERN = /<(?:[A-Za-z][\w.-]*:)?invoke\b|<\/(?:[A-Za-z][\w.-]*:)?invoke>|<(?:[A-Za-z][\w.-]*:)?parameter\s+name=|<\/(?:[A-Za-z][\w.-]*:)?parameter>|<(?:[A-Za-z][\w.-]*:)?function_calls>|<\/(?:[A-Za-z][\w.-]*:)?function_calls>|<\/?read-files?>|<modified-files>|<bash\b|<\/bash>|<read\b|<\/read>|<write\b|<\/write>|<edit\b|<\/edit>|<browse\b|<\/browse>|<ls\b|<\/ls>|<dir\b|<\/dir>|<tool_code\b|<\/tool_code>|<(?:[A-Za-z][\w.-]*:)?tool_call\b|<\/(?:[A-Za-z][\w.-]*:)?tool_call>|```(?:bash|sh|cmd|powershell|ps1)\b/i;

// A JSON payload shaped like a tool call — the shape a model reaches for when
// it "describes" tool calls instead of emitting them, e.g.
//   ```json
//   [{"tool": "Read", "arguments": {"path": "README.md"}}]
//   ```
// FAKE_TOOL_CALL_PATTERN misses this entirely: it only knows XML-ish tags and
// ```bash fences, so such a turn ended with zero tool calls, zero strikes and
// zero signal — the agent simply stalled. Both a name key AND an argument key
// are required so ordinary JSON the model prints as an *answer* (a config
// snippet, an API response) does not trip the guard.
const JSON_TOOL_NAME_KEY = /"(?:tool|tool_name|name|function|function_name|recipient_name)"\s*:\s*"[A-Za-z0-9_.\-]+"/i;
const JSON_TOOL_ARGS_KEY = /"(?:arguments|args|input|parameters|params|tool_input)"\s*:\s*[{[]/i;

function looksLikeJsonToolCall(text: string): boolean {
  return JSON_TOOL_NAME_KEY.test(text) && JSON_TOOL_ARGS_KEY.test(text);
}

function looksLikeFakeToolCall(text: string): boolean {
  return FAKE_TOOL_CALL_PATTERN.test(text) || looksLikeJsonToolCall(text);
}

// Pi's built-in tools, verified against the installed engine's
// dist/core/tools/*.js: bash, edit, find, grep, ls, read, write. Anything the
// auto-correction message names must be one of these — telling the model to
// call `read_file` (which does not exist in Pi) just produces another failed
// turn, which is how a single miss turns into a loop.
const PI_TOOLS = new Set(["bash", "edit", "find", "grep", "ls", "read", "write"]);

// Tools this harness registers through its own bridges. They are NOT Pi
// built-ins, but they are entirely real, and the correction message must never
// imply otherwise.
//
// Observed doing exactly that: the model emitted a Claude-style
// `<function_calls><invoke name="web_search">` fake call, the transformer
// correctly caught it, and then told the model "'web_search' is not a built-in
// tool for Pi — only bash, edit, find, grep, ls, read, write are available".
// The model's own reasoning recorded the contradiction: "the user explicitly
// asked me to call web_search... the system is now saying web_search isn't
// available and I should use one of the others. This is contradictory." It
// burned all three strikes and handed back to the user asking whether it should
// simulate a search with curl.
//
// A guard that talks the model out of a tool that exists is worse than no
// guard. Keep this in sync with the tools the bridges register.
const HARNESS_TOOLS = new Set([
  "web_search", "web_open", "web_snapshot", "web_click", "web_type",
  "web_press", "web_scroll", "web_screenshot", "web_evaluate",
  "deep_research",
  "bg_start", "bg_status", "bg_cancel",
]);

function isKnownTool(name: string): boolean {
  return PI_TOOLS.has(name) || HARNESS_TOOLS.has(name);
}

/** Tools that reach a network. Declared, not derived from a name prefix: the
 * question a denial branch asks is "could this session have searched?", and
 * `bg_start` shares the harness list without being able to. */
const WEB_TOOLS = new Set([
  "web_search", "web_open", "web_snapshot", "web_click", "web_type",
  "web_press", "web_scroll", "web_screenshot", "web_evaluate",
  "deep_research",
]);

/** What this session can ACTUALLY call, asked of Pi rather than assumed.
 *
 * `PI_TOOLS` is the built-in list and nothing more; every correction that
 * recited it was silently telling the model that the bridges' own tools did not
 * exist. On the denial path that was the whole defect — a model refusing for
 * want of web access was handed seven filesystem tools.
 *
 * Falls back to the built-ins when the runtime does not expose the call (older
 * Pi, or a test double). The fallback under-reports, which keeps the failure on
 * the safe side: this guard may then stay silent, but it will not claim a tool
 * that is not there. */
function activeToolNames(pi: ExtensionAPI): string[] {
  try {
    const got = (pi as { getActiveTools?: () => unknown }).getActiveTools?.();
    if (Array.isArray(got)) {
      const names = got.filter((n): n is string => typeof n === "string" && n.length > 0);
      if (names.length) return names;
    }
  } catch {}
  return [...PI_TOOLS];
}

function webToolsAmong(names: string[]): string[] {
  return names.filter((n) => WEB_TOOLS.has(n));
}

/** Active tools that act on this machine. Goes through TOOL_ALIASES rather than
 * testing PI_TOOLS membership directly: a session may register `read_file`
 * instead of `read`, and answering "I cannot read your files" with an empty list
 * — or with silence — is the same failure as answering it with the wrong list. */
function localToolsAmong(names: string[]): string[] {
  return names.filter((n) =>
    PI_TOOLS.has(n) || PI_TOOLS.has(TOOL_ALIASES[n.toLowerCase()] ?? ""));
}

const TOOL_ALIASES: Record<string, string> = {
  read: "read", read_file: "read", readfile: "read", view: "read", cat: "read", open_file: "read", get_file: "read",
  write: "write", write_file: "write", writefile: "write", create_file: "write", create: "write", str_replace_editor: "edit",
  edit: "edit", edit_file: "edit", str_replace: "edit", apply_patch: "edit", replace: "edit",
  bash: "bash", shell: "bash", sh: "bash", run: "bash", run_command: "bash", command: "bash", terminal: "bash",
  execute: "bash", execute_command: "bash", exec: "bash", cmd: "bash", powershell: "bash",
  ls: "ls", dir: "ls", list: "ls", list_dir: "ls", list_files: "ls", listdirectory: "ls", list_directory: "ls",
  grep: "grep", search: "grep", ripgrep: "grep", rg: "grep", search_files: "grep", codebase_search: "grep",
  find: "find", glob: "find", file_search: "find", find_files: "find",
};

// Argument-key synonyms, normalized to the parameter names in Pi's schemas
// (read/write/edit/ls/grep/find take `path`; bash takes `command`; grep/find
// take `pattern`).
const ARG_ALIASES: Record<string, string> = {
  file_path: "path", filepath: "path", filename: "path", file: "path", absolute_path: "path",
  target_file: "path", dir: "path", directory: "path", folder: "path",
  cmd: "command", script: "command", shell_command: "command", commandline: "command",
  regex: "pattern", search: "pattern",
  text: "content", contents: "content", body: "content", new_text: "content",
};

// `query` means different things to different tools, so it cannot live in the
// table above. grep and find take `pattern`; web_search and deep_research take
// `query` and renaming it BREAKS them.
//
// Observed live: the model produced a correct
// `{"name":"web_search","arguments":{"query":"pi-mono by badlogic"}}`, this
// canonicalizer rewrote query -> pattern, the correction message told the model
// to use `pattern`, and its next two attempts dutifully used the wrong argument
// name. The guard corrupted a call that had been right.
const PATTERN_TOOLS = new Set(["grep", "find"]);

function canonicalizeToolName(name: string): string {
  const key = String(name).trim().toLowerCase().replace(/[\s-]+/g, "_");
  return TOOL_ALIASES[key] ?? key;
}

function canonicalizeArgs(toolName: string, args: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(args ?? {})) {
    const lower = k.toLowerCase();
    let canonical = ARG_ALIASES[lower] ?? k;
    // `query` -> `pattern` only where `pattern` is the real parameter name.
    if (lower === "query") canonical = PATTERN_TOOLS.has(toolName) ? "pattern" : "query";
    // Never let an alias clobber a key the model already spelled correctly.
    if (!(canonical in out) || out[canonical] === undefined) out[canonical] = v;
  }
  // `ls` on a bare string arg, `bash` given a path, ... are left alone: fail
  // open and let the model re-issue rather than invent arguments.
  if (toolName === "ls" && typeof out.path !== "string" && typeof out.command === "string") {
    out.path = out.command;
    delete out.command;
  }
  return out;
}

// Arguments carried by child tags rather than by the tag body:
//
//     <read><path>README.md</path></read>
//     <tool_call><function=read><parameter=path>README.md</parameter></function></tool_call>
//
// Both shapes were observed live. Without this the body was taken verbatim, so
// `path` became the string `<path>README.md</path>` and the correction message
// handed those broken arguments back to the model.
const PARAM_TAG_PATTERN = /<parameter(?:\s+name\s*=\s*["']([^"']+)["']|\s*=\s*([a-zA-Z0-9_.-]+))\s*>([\s\S]*?)<\/parameter>/gi;
const CHILD_TAG_PATTERN = /<([a-zA-Z_][a-zA-Z0-9_.-]*)\s*>([\s\S]*?)<\/\1>/g;

// Names a child tag may carry as an argument. Anything else is content: a
// `<write>` whose `<content>` embeds `<div>hi</div>` must not gain a `div`
// argument. Falls back to every child tag when none of them is recognized, so
// an argument name this table has never seen still reaches the model.
const ARG_TAG_NAMES = new Set<string>([
  ...Object.keys(ARG_ALIASES),
  ...Object.values(ARG_ALIASES),
  "query",
]);

// Arguments carried as <arg_key>/<arg_value> pairs — the shape Laguna-S-2.1's
// built-in chat template emits. Its Jinja runs `tojson` on every value that is
// not already a string, so `5` arrives as a number literal and `a.txt` arrives
// raw; parsing the JSON back is what keeps an integer argument an integer
// instead of the string "5" in the correction message.
const ARG_KV_PATTERN = /<arg_key>([\s\S]*?)<\/arg_key>\s*<arg_value>([\s\S]*?)<\/arg_value>/gi;

function decodeArgValue(raw: string): unknown {
  const trimmed = raw.trim();
  // Only JSON-decode payloads that look like JSON. Bare prose such as
  // `git status --short` must stay a string, and `null` typed by a model as a
  // filename should not silently become the null value.
  if (!/^(?:".*"|-?\d+(?:\.\d+)?|true|false|\[[\s\S]*\]|\{[\s\S]*\})$/s.test(trimmed)) return trimmed;
  try {
    return JSON.parse(trimmed);
  } catch {
    return trimmed;
  }
}

function extractArgKeyValueArgs(body: string): Record<string, unknown> {
  const args: Record<string, unknown> = {};
  for (const m of body.matchAll(ARG_KV_PATTERN)) {
    const key = m[1].trim();
    if (key) args[key] = decodeArgValue(m[2]);
  }
  return args;
}

function extractChildTagArgs(body: string): Record<string, unknown> {
  const explicit: Record<string, unknown> = {};
  for (const m of body.matchAll(PARAM_TAG_PATTERN)) {
    const key = m[1] ?? m[2];
    if (key) explicit[key] = m[3].trim();
  }
  if (Object.keys(explicit).length > 0) return explicit;

  const all: Record<string, unknown> = {};
  const recognized: Record<string, unknown> = {};
  for (const m of body.matchAll(CHILD_TAG_PATTERN)) {
    const key = m[1];
    const value = m[2].trim();
    if (!(key in all)) all[key] = value;
    if (ARG_TAG_NAMES.has(key.toLowerCase())) recognized[key] = value;
  }
  return Object.keys(recognized).length > 0 ? recognized : all;
}

interface ParsedToolTag {
  name: string;
  args: Record<string, unknown>;
  raw: string;
  /** How many tool calls the payload described; >1 means the model batched them. */
  count?: number;
  /** True when the canonical name is not one of Pi's built-in tools. */
  unknownTool?: boolean;
  /** Trailing lines dropped as command OUTPUT rather than command. See
   * dropEchoedOutputLines — these are named back to the model, because a parse
   * it cannot see is a parse it cannot correct. */
  droppedLines?: string[];
}

// Lines that are a command's OUTPUT, not a command.
//
// Session 019ffbdd, third transformer correction: the parsed `command` was
//
//     git add README.md docs/
//     git commit -m "整理專案結構，新增 README.md 與 docs 指南"
//     commit fe56ec6
//
// The last line is git's own echo, which the model had written inside its
// ```bash block. The parser took the block faithfully and then ordered the model
// to run all three 【立即且只能】. Nothing between the model's text and a bash
// argument asked whether that text was a command at all.
//
// Deliberately narrow and derived from what was observed, not from imagination:
// every pattern here is unambiguous output with no plausible reading as a
// command. Only TRAILING lines are dropped — output in the middle of a block is
// ambiguous, and guessing there would start deleting real commands.
const ECHOED_OUTPUT_LINE = [
  /^commit\s+[0-9a-f]{7,40}$/i,
  /^[0-9a-f]{7,40}$/i,
  /^\[[^\]\s]+\s+[0-9a-f]{7,40}\]\s/,
  /^\s*\d+\s+files?\s+changed/i,
  /^\s*\d+\s+(?:insertions?|deletions?)\b/i,
  /^\s*(?:create|delete|rename)\s+mode\s/i,
  /^On branch\s/i,
  /^nothing to commit/i,
  /^Author:\s/i,
  /^Date:\s/i,
];

export function dropEchoedOutputLines(command: string): { command: string; dropped: string[] } {
  if (typeof command !== "string" || !command.includes("\n")) {
    return { command, dropped: [] };
  }
  const lines = command.split("\n");
  const dropped: string[] = [];
  while (lines.length > 1) {
    const last = lines[lines.length - 1];
    if (!last.trim()) { lines.pop(); continue; }
    if (!ECHOED_OUTPUT_LINE.some((re) => re.test(last.trim()))) break;
    dropped.unshift(lines.pop() as string);
  }
  if (!dropped.length) return { command, dropped: [] };
  return { command: lines.join("\n"), dropped };
}

// Normalizes a raw {name, args} pair into Pi's tool vocabulary.
function toParsedTag(rawName: string, rawArgs: Record<string, unknown>, raw: string, count = 1): ParsedToolTag {
  const name = canonicalizeToolName(rawName);
  const args = canonicalizeArgs(name, rawArgs);
  // Every branch of parseUniversalToolTag funnels through here, so the shape
  // check belongs here rather than in the one branch that happened to be caught
  // producing output-as-command.
  let droppedLines: string[] | undefined;
  if (name === "bash" && typeof args.command === "string") {
    const { command, dropped } = dropEchoedOutputLines(args.command);
    if (dropped.length) {
      args.command = command;
      droppedLines = dropped;
    }
  }
  return { name, args, raw, count, unknownTool: !isKnownTool(name), droppedLines };
}

// Extracts every tool-call-shaped object from a JSON payload, fenced or bare,
// object or array. Returns [] when nothing matches.
function extractJsonToolCalls(text: string): { name: string; args: Record<string, unknown> }[] {
  const candidates: string[] = [];
  const fenced = text.match(/```(?:json|tool|tool_call|tool_calls|toolcode)?\s*([\s\S]*?)```/gi) ?? [];
  for (const block of fenced) {
    candidates.push(block.replace(/^```[a-z_]*\s*/i, "").replace(/```$/, "").trim());
  }
  // Bare (unfenced) payloads too — some models drop the fence entirely. A
  // non-greedy regex is wrong here: it stops at the first `}`, which is the
  // *nested* arguments object, yielding invalid JSON. Scan for balanced
  // delimiters instead.
  candidates.push(...extractBalancedJsonSpans(text));

  for (const candidate of candidates) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(candidate);
    } catch {
      continue;
    }
    const items = Array.isArray(parsed) ? parsed : [parsed];
    const calls: { name: string; args: Record<string, unknown> }[] = [];
    for (const item of items) {
      if (!item || typeof item !== "object") continue;
      const o = item as Record<string, unknown>;
      const nameRaw = o.tool ?? o.name ?? o.tool_name ?? o.function ?? o.function_name ?? o.recipient_name;
      const name = typeof nameRaw === "string" ? nameRaw : typeof (nameRaw as { name?: unknown })?.name === "string" ? (nameRaw as { name: string }).name : null;
      if (!name) continue;
      // An argument key is mandatory. Without it, `{"name": "my-skill",
      // "description": "..."}` — ordinary JSON a model prints as its ANSWER —
      // would be hijacked into a bogus tool call.
      const hasArgsKey = ["arguments", "args", "input", "parameters", "params", "tool_input"].some((k) => k in o);
      if (!hasArgsKey) continue;
      const argsRaw = o.arguments ?? o.args ?? o.input ?? o.parameters ?? o.params ?? o.tool_input ?? {};
      const args = (typeof argsRaw === "string" ? safeJsonObject(argsRaw) : argsRaw) as Record<string, unknown>;
      calls.push({ name, args: args && typeof args === "object" ? args : {} });
    }
    if (calls.length > 0) return calls;
  }
  return [];
}

// Returns each top-level {...} / [...] span in the text, delimiter-balanced and
// string-aware (so a `}` inside a JSON string value doesn't end the span).
//
// SCAN_BUDGET bounds the work: an unbalanced opener restarts the inner scan one
// character later, which is O(n²) on pathological input (a wall of `{`). This
// runs on every turn_end, so an unbounded scan would let one malformed message
// hang the whole session — the opposite of what a loop guard is for.
const JSON_SCAN_BUDGET = 200_000;

function extractBalancedJsonSpans(text: string, maxSpans = 5): string[] {
  const spans: string[] = [];
  let budget = JSON_SCAN_BUDGET;
  for (let i = 0; i < text.length && spans.length < maxSpans && budget > 0; i++) {
    const open = text[i];
    if (open !== "{" && open !== "[") continue;
    const close = open === "{" ? "}" : "]";
    let depth = 0;
    let inString = false;
    let escaped = false;
    for (let j = i; j < text.length && budget-- > 0; j++) {
      const ch = text[j];
      if (inString) {
        if (escaped) escaped = false;
        else if (ch === "\\") escaped = true;
        else if (ch === '"') inString = false;
        continue;
      }
      if (ch === '"') inString = true;
      else if (ch === open) depth++;
      else if (ch === close) {
        depth--;
        if (depth === 0) {
          spans.push(text.slice(i, j + 1));
          i = j;
          break;
        }
      }
    }
  }
  return spans;
}

function safeJsonObject(raw: string): Record<string, unknown> {
  try {
    const v = JSON.parse(raw);
    return v && typeof v === "object" ? (v as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

// Parsing the intent is only half the job. The transformer used to stop there
// and ask the model to re-issue the call natively — but a model able to do that
// would not have emitted markup in the first place, so three asks in a row ended
// the session by design.
//
// Pi gives extensions no way to run a tool on the model's behalf (verified
// against the installed engine's dist/core/extensions/types.d.ts: sendMessage,
// sendUserMessage, appendEntry and exec — there is no executeTool), so for
// read-only intents this bridge does the work itself and feeds the result back.
// Read-only strictly: `write`, `edit` and `bash` are never performed for the
// model, and the target must satisfy the same containment rule the tool_call
// guard enforces.
const AUTO_EXEC_CHAR_BUDGET = 8000;
const AUTO_EXEC_MAX_ENTRIES = 200;

export function autoExecuteReadOnly(
  parsed: { name: string; args: Record<string, unknown> },
  cwd: unknown,
): { path: string; text: string } | null {
  if (parsed.name !== "read" && parsed.name !== "ls") return null;
  const raw = typeof parsed.args?.path === "string" ? parsed.args.path : "";
  if (!raw || typeof cwd !== "string" || !cwd) return null;

  let root: string, target: string;
  try {
    root = resolve(cwd);
    target = resolve(root, raw);
  } catch {
    return null;
  }
  const rel = relative(root, target);
  if (rel !== "" && (rel.startsWith("..") || isAbsolute(rel))) return null;
  if (!existsSync(target)) return null;

  try {
    const stat = statSync(target);
    if (stat.isDirectory()) {
      const all = readdirSync(target);
      const shown = all.slice(0, AUTO_EXEC_MAX_ENTRIES);
      const note = all.length > shown.length ? `\n… (truncated, ${all.length} entries total)` : "";
      return { path: target, text: shown.join("\n") + note };
    }
    if (!stat.isFile()) return null;
    const body = readFileSync(target, "utf-8");
    // An unbounded paste back into context is the failure mode this harness
    // already paid for once. Cap it and say so.
    const text =
      body.length > AUTO_EXEC_CHAR_BUDGET
        ? body.slice(0, AUTO_EXEC_CHAR_BUDGET) +
          `\n… (truncated at ${AUTO_EXEC_CHAR_BUDGET} of ${body.length} chars — re-read with an offset for the rest)`
        : body;
    return { path: target, text };
  } catch {
    return null; // unreadable for any reason — fall back to the normal correction
  }
}

export function parseUniversalToolTag(text: string): ParsedToolTag | null {
  if (!text || typeof text !== "string") return null;

  // 0. JSON tool-call payloads (```json [{"tool": ..., "arguments": ...}] ```,
  //    a single object, fenced or bare). Checked first: it is the shape most
  //    local models fall back to, and the old parser only matched a fenced
  //    object whose FIRST key was literally "name".
  const jsonCalls = extractJsonToolCalls(text);
  if (jsonCalls.length > 0) {
    const first = jsonCalls[0];
    return toParsedTag(first.name, first.args, text.trim(), jsonCalls.length);
  }

  // 1a. The namespaced Anthropic-style dialect
  //     (runs BEFORE branch 1: branch 1 matches the <invoke> wrapper, fails to
  //     JSON-parse a <parameter> body, and falls back to a name with EMPTY
  //     args — a correction that names the tool and drops every argument), which is what the chat template
  //     served on 2026-08-13 taught:
  //
  //       <atem:function_calls>
  //       <atem:invoke name="write">
  //       <atem:parameter name="path">x.md</atem:parameter>
  //       </atem:invoke>
  //       </atem:function_calls>
  //
  //     Branch 1 cannot see it: its pattern is `<invoke\b`, and `<atem:invoke`
  //     does not match. The same prefix hid this dialect from
  //     FAKE_TOOL_CALL_PATTERN, so a turn that leaked the whole block as text
  //     produced no strike and no correction — the silent stall this parser
  //     exists to end, reappearing because a namespace was not anticipated.
  //     The prefix is optional here, so the unprefixed spelling lands in the
  //     same branch rather than in two places that can drift apart.
  const invokeMatch = text.match(
    /<(?:[A-Za-z][\w.-]*:)?invoke\s+name=["']([^"']+)["']\s*>([\s\S]*?)<\/(?:[A-Za-z][\w.-]*:)?invoke>/i);
  if (invokeMatch) {
    const args: Record<string, unknown> = {};
    const paramRe =
      /<(?:[A-Za-z][\w.-]*:)?parameter\s+name=["']([^"']+)["']\s*>([\s\S]*?)<\/(?:[A-Za-z][\w.-]*:)?[^<>\s]{0,24}>/gi;
    for (const p of invokeMatch[2].matchAll(paramRe)) {
      args[p[1]] = p[2];
    }
    // A closing tag whose name decoded wrong is exactly how this dialect showed
    // up in real arguments (`</atem:日>`), so the parameter pattern above
    // deliberately does not require the closing tag's name to match. The trade
    // is that it would also close on an unrelated tag; requiring at least one
    // parameter keeps `<invoke>` wrapped around prose out.
    const count = [...text.matchAll(/<(?:[A-Za-z][\w.-]*:)?invoke\s+name=/gi)].length;
    if (Object.keys(args).length > 0) {
      return toParsedTag(invokeMatch[1], args, invokeMatch[0], count);
    }
  }

  // 1. Standard XML tool wrappers: <tool_code>, <invoke>, <tool_call>, <function_call>, <action>, <execute>
  //    Fenced ```json payloads are NOT handled here: step 0 already covers
  //    them and enforces the "must carry an argument key" gate. The old
  //    fenced-object pattern here required no such gate, so it hijacked any
  //    ```json block whose first key happened to be "name" — e.g. a skill
  //    frontmatter snippet the model was legitimately showing the user.
  const tagPatterns = [
    /<(?:tool_code|invoke|tool_call|function_call|action|execute)\b[^>]*>([\s\S]*?)<\/(?:tool_code|invoke|tool_call|function_call|action|execute)>/i,
  ];

  for (const pattern of tagPatterns) {
    const match = text.match(pattern);
    if (match && match[1]) {
      const rawContent = match[1].trim();
      try {
        const parsed = JSON.parse(rawContent);
        if (parsed && typeof parsed === "object" && typeof parsed.name === "string") {
          const name = parsed.name;
          const args = (parsed.arguments || parsed.input || parsed.parameters || {}) as Record<string, unknown>;
          return toParsedTag(name, args, match[0]);
        }
      } catch {
        const nameMatch = text.match(/<invoke\s+name=["']([^"']+)["']/i) || text.match(/<tool_code\s+name=["']([^"']+)["']/i);
        if (nameMatch && nameMatch[1]) {
          return toParsedTag(nameMatch[1], {}, match[0]);
        }
      }
    }
  }

  // 1b. The format the local chat template actually teaches
  //     (`C:\models\chat_template.jinja`, qwen3.6-froggeric-v21.3):
  //     <tool_call><function=NAME><parameter=key>value</parameter></function>.
  //     llama.cpp parses this into a real tool call while generation holds up;
  //     when it degrades under a large prompt the markup leaks into the message
  //     text instead. Every branch here used to miss it — step 1 matches the
  //     <tool_call> wrapper but bails when the body is not JSON — so the turn
  //     ended with no strike, no correction and no signal to the user.
  const fnMatch = text.match(/<function\s*=\s*([a-zA-Z0-9_.-]+)\s*>([\s\S]*?)<\/function>/i);
  if (fnMatch) {
    const wrapper = text.match(/<tool_call>[\s\S]*?<\/tool_call>/i);
    const fnCount = [...text.matchAll(/<function\s*=\s*[a-zA-Z0-9_.-]+\s*>/gi)].length;
    return toParsedTag(fnMatch[1], extractChildTagArgs(fnMatch[2]), wrapper?.[0] ?? fnMatch[0], fnCount);
  }

  // 1c. The format Laguna-S-2.1's built-in chat template teaches:
  //     <tool_call>NAME<arg_key>key</arg_key><arg_value>value</arg_value></tool_call>
  //     The name is bare text right after the wrapper, with no <function=> around
  //     it, so branch 1b cannot see it and branch 1 bails on the non-JSON body.
  //     That is the same silent-stall hole that ```json arrays and Qwen's
  //     <function=> shape each fell through before — a template teaches a format,
  //     the parser has no branch for it, and a degraded turn leaks it as text
  //     with no strike and no correction. Requiring at least one <arg_key> pair
  //     keeps `<tool_call>` wrapped around prose from being read as a call.
  const lagunaCalls = [
    ...text.matchAll(
      /<tool_call>\s*([a-zA-Z0-9_.-]+)\s*((?:<arg_key>[\s\S]*?<\/arg_value>\s*)+)<\/tool_call>/gi,
    ),
  ];
  if (lagunaCalls.length > 0) {
    const [raw, name, argBody] = lagunaCalls[0];
    const args = extractArgKeyValueArgs(argBody);
    if (Object.keys(args).length > 0) {
      return toParsedTag(name, args, raw, lagunaCalls.length);
    }
  }

  // 2. Specific tool XML tags: <read>, <write>, <edit>, <bash>, <ls>, <dir>, <browse>, <search>, <command>, <terminal>, <read_file>, <write_file>
  const anthropicTagPattern = /<(read|write|edit|bash|ls|dir|browse|search|command|terminal|read_file|write_file)\b[^>]*>([\s\S]*?)<\/\1>/i;
  const matchAnthropic = text.match(anthropicTagPattern);
  if (matchAnthropic && matchAnthropic[1] && matchAnthropic[2]) {
    const tagName = matchAnthropic[1].toLowerCase();
    const rawBody = matchAnthropic[2].trim();

    // canonicalizeToolName covers read/read_file -> read, ls/dir -> ls,
    // command/terminal -> bash. `browse`/`search` have no built-in Pi
    // equivalent and stay as-is (flagged unknownTool by toParsedTag).
    const toolName = canonicalizeToolName(tagName);

    let args: Record<string, unknown> = {};
    if (rawBody.startsWith("{") && rawBody.endsWith("}")) {
      try { args = JSON.parse(rawBody); } catch {}
    }

    // Child tags before the body heuristics below: `<read><path>x</path></read>`
    // has a body, it just is not the argument value.
    if (Object.keys(args).length === 0) {
      args = extractChildTagArgs(rawBody);
    }

    if (Object.keys(args).length === 0) {
      if (toolName === "bash") {
        args = { command: rawBody };
      } else if (toolName === "ls") {
        const pathMatch = rawBody.match(/"path"\s*:\s*"([^"]+)"/) || rawBody.match(/["']([^"']+)["']/);
        args = { path: pathMatch ? pathMatch[1] : (rawBody.trim() || ".") };
      } else if (toolName === "read") {
        const pathMatch = rawBody.match(/"(?:file_path|path|filePath|filename|file)"\s*:\s*"([^"]+)"/) || rawBody.match(/["']([^"']+)["']/);
        if (pathMatch) args = { path: pathMatch[1] };
        else args = { path: rawBody.trim() };
      } else if (toolName === "write" || toolName === "edit") {
        const pathMatch = rawBody.match(/"(?:file_path|path|filePath|filename|file)"\s*:\s*"([^"]+)"/);
        const path = pathMatch ? pathMatch[1] : "";
        args = { path, content: rawBody };
      }
    }

    return toParsedTag(toolName, args, matchAnthropic[0]);
  }

  // 3. Markdown Bash code blocks: ```bash command ``` or ```sh command ```
  const bashBlockPattern = /```(?:bash|sh|cmd|powershell|ps1)\s*([\s\S]*?)\s*```/i;
  const matchBashBlock = text.match(bashBlockPattern);
  if (matchBashBlock && matchBashBlock[1]) {
    const rawBody = matchBashBlock[1].trim();
    if (rawBody) {
      let toolName = "bash";
      let args: Record<string, unknown> = { command: rawBody };
      if (rawBody.startsWith("read ") || rawBody.startsWith("cat ")) {
        toolName = "read";
        const targetPath = rawBody.replace(/^(?:read|cat)\s+/, "").trim();
        args = { path: targetPath };
      }
      return toParsedTag(toolName, args, matchBashBlock[0]);
    }
  }

  // 4. Standalone JSON object in text with "name" and "arguments" / "path" / "command"
  const jsonMatch = text.match(/\{\s*"name"\s*:\s*"([a-zA-Z0-9_\-]+)"\s*,\s*"(?:arguments|input|parameters|path|command|file_path)"\s*:[\s\S]*?\}/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[0]);
      if (parsed && typeof parsed.name === "string") {
        const name = parsed.name;
        const args = (parsed.arguments || parsed.input || parsed.parameters || parsed) as Record<string, unknown>;
        delete args.name;
        return toParsedTag(name, args, jsonMatch[0]);
      }
    } catch {}
  }

  return null;
}

function extractMessageText(message: unknown): string {
  const content = (message as { content?: unknown } | undefined)?.content;
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content
    .filter((c): c is { text: string } => !!c && typeof (c as { text?: unknown }).text === "string")
    .map((c) => c.text)
    .join("\n");
}

// README documents `enableUniversalTagTransformer` and
// `enableSelfHealingLoopGuard` in pi-config/harness-config.json as the fix for
// "<tool_code> 標籤卡死 / 死鎖停擺". Until now nothing read either key: they were
// decorative, so following the documented remedy changed nothing. Both are
// honored here, defaulting to on (absent config == current behavior).
interface LoopGuardConfig {
  enableUniversalTagTransformer: boolean;
  enableSelfHealingLoopGuard: boolean;
}

// Deliberately NOT cached, matching taste-bridge / case-bridge /
// planning-with-files-bridge: every bridge re-reads harness-config.json per
// turn, so a flag edit takes effect on the next turn everywhere. A cache here
// would have made this one flag alone require a restart — and "I flipped the
// switch and nothing happened" is exactly the experience that made these flags
// look like zombies in the first place. The file is under 1KB.
function loopGuardConfig(): LoopGuardConfig {
  const config: LoopGuardConfig = { enableUniversalTagTransformer: true, enableSelfHealingLoopGuard: true };
  try {
    // import.meta.url, not require.resolve: Pi's loader shims `require` for
    // bridges, but bare `node` does not for an ESM-declared package — and
    // importing this file in node is how the guard gets behaviourally tested.
    // Under require.resolve the throw would be swallowed by this catch and
    // silently return the defaults, i.e. look exactly like a working config.
    const here = dirname(fileURLToPath(import.meta.url));
    const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf-8"));
    const harnessRoot = pkg["pi-harness"]?.root || join(here, "../..");
    const cfgPath = join(harnessRoot, "pi-config", "harness-config.json");
    if (existsSync(cfgPath)) {
      const cfg = JSON.parse(readFileSync(cfgPath, "utf8"));
      if (cfg.enableUniversalTagTransformer === false) config.enableUniversalTagTransformer = false;
      if (cfg.enableSelfHealingLoopGuard === false) config.enableSelfHealingLoopGuard = false;
    }
  } catch {}
  return config;
}

let consecutiveFakeToolStrikes = 0;
// The transformer used to reset consecutiveFakeToolStrikes on every hit, so a
// model that kept emitting parseable-but-fake calls could be auto-retried
// forever (each retry sets triggerTurn: true). This counter caps that path on
// its own budget and hands control back to the human at 3.
let consecutiveTransformStrikes = 0;
// Read-only intents the bridge performed for the model. Kept apart from the
// strike counters because serving is progress, not a failed correction — but
// bounded, or a model that never issues a native call gets fed forever.
let consecutiveServedTurns = 0;
const AUTO_EXEC_MAX_TURNS = 8;

// Guard 6: a turn that ends cleanly having done nothing.
//
// Measured 2026-07-29 (23,284 prompt tokens, 13 tools, both quants): 0/6 turns
// produced a tool call. The model ends with finish_reason=stop and either
// denies the capability it was just handed ("I don't have direct access to your
// local filesystem") or claims work it never did ("File `x.py` read. Stopping
// as instructed."). One run fabricated the whole file into a ```python block.
//
// Invisible to everything else here: no tool call to inspect, no markup for
// FAKE_TOOL_CALL_PATTERN, nothing for the loop guard to count. This is the
// dominant failure at this prompt scale, and it had no guard at all.
// The Chinese branch used to be a bare `無法(?:直接)?(?:存取|讀取|訪問)` — a verb
// with no object, where the English branch had always required a filesystem
// noun. Measured on session 019ffbba: the model truthfully wrote 「亦無法訪問暗網」
// (it cannot reach the dark web), the guard matched that, and answered
// 「你剛才說沒有檔案系統存取權」 — a sentence the model never wrote — then listed
// seven tools, none of which reach a network. The model accepted the correction,
// abandoned the intelligence task it had been given, and emitted
// `pwd && ls -la && whoami` instead. A guard that corrects a truthful turn does
// not just waste a turn; this one chose the turn's next action.
//
// The object is now required, and the gap cannot cross sentence-ending
// punctuation, so 「無法訪問暗網。因此…」 stops at the 。.
const CAPABILITY_DENIAL = /(?:do(?:n['’]?t| not)|cannot|can['’]?t|no)\s+(?:have\s+)?(?:direct(?:ly)?\s+|live\s+)?access\s+(?:to\s+)?(?:your|the|this)?\s*(?:local\s+)?(?:file\s?system|files?|repositor|folder|director|machine|disk)|無法(?:直接|即時|實時)?(?:存取|讀取|訪問|進入|開啟)[^。！？!?\n]{0,16}?(?:檔案系統|文件系統|檔案|文件|目錄|資料夾|磁碟|硬碟|本機|本地端|儲存空間|repo|repository|專案)/i;

// The denial this harness had no answer for at all. Same session: the model's
// FIRST turn declined the whole task with 「無法即時存取網路實時搜尋」 while
// stealth-web-bridge was installed and web_search was live. Nothing spoke,
// because every guard here was written for the filesystem.
//
// Fired only when a matching tool is actually active — see webToolsAmong. A
// model that says it cannot browse in a session with no web tools is right, and
// telling it otherwise is the mirror of the mistake documented above
// HARNESS_TOOLS.
const WEB_DENIAL = /(?:do(?:n['’]?t| not)|cannot|can['’]?t|no)\s+(?:have\s+)?(?:direct(?:ly)?\s+|live\s+|real[\s-]?time\s+)?(?:internet|web|network|online)\s+access|(?:cannot|can['’]?t|unable\s+to)\s+(?:browse|search|access)\s+(?:the\s+)?(?:internet|web|online)|無法(?:直接|即時|實時)?(?:存取|讀取|訪問|連上|進入|瀏覽|搜尋|查詢)[^。！？!?\n]{0,16}?(?:網路|網際網路|網頁|線上|即時搜尋|實時搜尋|網站|暗網)/i;
// Claiming a read/run. Deliberately narrow: it must look like a report of a
// completed action, not a plan ("I will read…") or a question.
// The last alternative was added 2026-07-30. Captured live at a 41,129-token
// prompt, the entire answer was `File read. Stopping as instructed.` — no
// filename and no "I have", so every other branch here missed it and the turn
// scored as an ordinary no-call with no correction. The claim is fabrication
// whether or not the model names the file.
//
// It is deliberately narrow: the noun phrase must be at the start of a sentence
// AND `read` must be followed by sentence-ending punctuation. That keeps prose
// about reads ("File read errors are logged", "the file read failed") out of it,
// because a guard that corrects a truthful turn teaches the model to distrust a
// correct answer — a worse failure than missing one fabrication.
const FABRICATED_COMPLETION = /(?:I(?:'ve| have)\s+(?:already\s+)?read|(?:File|The file)\s+[`"'][^`"']+[`"']\s+(?:has been\s+)?read\b|已(?:經)?讀取|已讀完|(?:^|[.!?]\s+|\n)\s*(?:The\s+)?(?:file|files|contents?|directory|dir)\s+read\s*(?=[.,;!]|$))/i;

// Whether a real tool call has EVER happened this session. "I have read X" is
// usually true once the model has actually used tools, and a guard that calls
// that a lie is worse than no guard.
let sawAnyRealToolCall = false;

// Guard 7 — a turn that announces its next step and then ends.
//
// Found by the 2026-07-30 real-session validation: five occurrences across six
// sessions, three of them inside deep-research sub-agents, accounting for three
// of the six tasks producing nothing usable. The shape is always the same —
// correct tool calls up to a point, then:
//
//     Real model paths in these scripts. Check existence:
//     I've read the code. Write failing test first.
//     Continuing to read the article:
//
// stopReason=stop, zero tool calls, and Pi exits `--print` because that is a
// well-formed turn. Every other guard is blind: there is no markup, nothing is
// repeated, and FABRICATED_COMPLETION matches claims of COMPLETED work, which
// is the semantic opposite of an announcement.
const NEXT_STEP_OPENER =
  /^(?:now\s+|next[,:]?\s+|then\s+|first[,:]?\s+)?(?:i(?:'ll|'m\s+going\s+to|\s+will|\s+am\s+going\s+to)\b|let(?:'s|\s+me)\b|check\b|verify\b|write\b|fetch\b|read\b|run\b|collect\b|continu(?:e|ing)\b|inspect\b|search\b|接下來|我(?:先|來)\b)/i;

// Handing a decision back is a correct terminal state. Re-triggering it talks
// over the user, which is a worse failure than leaving one stall unnudged.
const ASKS_THE_USER = /[?？]\s*$|嗎[?？]?\s*$|如果你(?:願意|想|需要)/;

function announcesUnfulfilledNextStep(text: string): boolean {
  const trimmed = String(text ?? "").trim();
  if (!trimmed) return false;
  if (ASKS_THE_USER.test(trimmed)) return false;
  // A message left hanging on a colon promised something that never arrived.
  if (/[:：]$/.test(trimmed)) return true;
  // Otherwise judge only the LAST sentence: "The issue: X used strict >.
  // Changed to >=." is a finished report whose middle happens to look forward.
  const sentences = trimmed.split(/(?<=[.!?。！？])\s+/).filter(Boolean);
  const last = (sentences[sentences.length - 1] ?? "").trim();
  return NEXT_STEP_OPENER.test(last);
}

// Guard 9 — a correct tool call thrown away because the turn overran the cap.
//
// Captured live 2026-07-31: usage output 16,384 (exactly maxTokens),
// stopReason=length, a 1,086-char think block and a short, valid
// `bash {"command":"python -m unittest discover -s tests"}`. Pi refused it —
// "the response hit the output token limit, so its arguments may be truncated"
// — and the session ended after ONE turn.
//
// Guard 4 cannot see it: that one inspects argument VALUES, and these were
// fine. The runaway is everything around the call.
// Pi still emits a toolResult when it refuses a truncated call — an error one
// carrying this phrase. Modelling it as "no result at all" is what made the
// first version of this guard pass its tests and do nothing in a real session:
// loopGuard returns early whenever toolResults is non-empty, so the check has
// to happen BEFORE that return, and has to tell a refused call apart from a
// command that simply failed.
const DISCARDED_CALL_RESULT = /output token limit|was not executed/i;

function toolResultsShowADiscardedCall(results: unknown): boolean {
  if (!Array.isArray(results)) return false;
  return results.some((r) => {
    const rec = r as { isError?: unknown; content?: unknown };
    if (!rec?.isError) return false;
    const c = rec.content;
    const text = typeof c === "string"
      ? c
      : Array.isArray(c) ? c.map((b) => (b as { text?: string })?.text ?? "").join(" ") : "";
    return DISCARDED_CALL_RESULT.test(text);
  });
}

let consecutiveDiscardedCalls = 0;
const MAX_DISCARDED_CALL_NUDGES = 2;

let consecutiveIntentNudges = 0;
// Two nudges, then stop. A model that keeps announcing instead of acting is a
// loop with extra steps, and nudging it forever is the deadlock this guard
// exists to break.
const MAX_INTENT_NUDGES = 2;

function loopGuard(event: { message: unknown; toolResults?: unknown[] }, ctx: ExtensionContext, pi: ExtensionAPI) {
  const hadRealToolCall = Array.isArray(event.toolResults) && event.toolResults.length > 0;
  const msg = (event as { message?: { stopReason?: unknown; content?: unknown } }).message;
  const overran = msg && (msg as { stopReason?: unknown }).stopReason === "length";
  const emittedACall =
    Array.isArray((msg as { content?: unknown })?.content) &&
    ((msg as { content: Array<{ type?: string }> }).content).some((b) => b?.type === "toolCall");

  // Env-gated shape dump. Guard 9 was written twice against an ASSUMED event
  // shape and did nothing in a real session both times, while its unit tests
  // passed — the fixtures encoded the assumption. Off unless the variable names
  // a file.
  if (process.env.PI_HARNESS_DUMP_TURN_END) {
    try {
      const m = (event as { message?: Record<string, unknown> }).message ?? {};
      writeFileSync(
        process.env.PI_HARNESS_DUMP_TURN_END,
        JSON.stringify({
          messageKeys: Object.keys(m),
          stopReason: (m as { stopReason?: unknown }).stopReason,
          contentTypes: Array.isArray((m as { content?: unknown }).content)
            ? ((m as { content: Array<{ type?: string }> }).content).map((b) => b?.type)
            : typeof (m as { content?: unknown }).content,
          toolResults: (event as { toolResults?: unknown }).toolResults,
          computed: {
            overran,
            emittedACall,
            discardedResult: toolResultsShowADiscardedCall((event as { toolResults?: unknown }).toolResults),
            consecutiveDiscardedCalls,
            MAX_DISCARDED_CALL_NUDGES,
          },
        }, null, 2) + "\n",
        { flag: "a" },
      );
    } catch {}
  }

  // Guard 9 runs FIRST: a discarded call arrives WITH a (failed) toolResult, so
  // every branch below — including the early return just under this — would
  // treat the turn as a normal tool-using turn and do nothing.
  if (overran && emittedACall && toolResultsShowADiscardedCall(event.toolResults)) {
    if (consecutiveDiscardedCalls < MAX_DISCARDED_CALL_NUDGES) {
      consecutiveDiscardedCalls += 1;
      ctx.ui.notify(
        `🚨 A tool call was discarded: the turn hit the output limit (nudge ${consecutiveDiscardedCalls}/${MAX_DISCARDED_CALL_NUDGES}).`,
        "error",
      );
      pi.sendMessage(
        {
          customType: "loop-guard",
          content:
            "[SYSTEM] 你這一輪發出了工具呼叫，但整個回覆撞到輸出上限，所以 Pi 沒有執行它。" +
            "問題不在呼叫本身，而在它前後的長篇輸出。\n" +
            "請立刻重新發出**同一個**呼叫，並且這次不要附帶任何說明或思考，簡短到只剩呼叫本身。",
          display: true,
        },
        { deliverAs: "followUp", triggerTurn: true },
      );
    }
    return;
  }

  if (hadRealToolCall) {
    sawAnyRealToolCall = true;
    consecutiveDiscardedCalls = 0;
    consecutiveFakeToolStrikes = 0;
    consecutiveTransformStrikes = 0;
    consecutiveServedTurns = 0;
    consecutiveIntentNudges = 0;
    return;
  }

  const cfg = loopGuardConfig();
  if (!cfg.enableSelfHealingLoopGuard && !cfg.enableUniversalTagTransformer) return;


  const text = extractMessageText(event.message);

  // Universal Tool Tag Transformer: intercept valid tool tags and auto-advance
  const parsedTag = cfg.enableUniversalTagTransformer ? parseUniversalToolTag(text) : null;
  if (parsedTag) {
    consecutiveFakeToolStrikes = 0;

    // Read-only intents are served, not re-asked. See autoExecuteReadOnly.
    // Serving does NOT consume a strike: a correction the model ignored and a
    // file the model now has are not the same event, and counting them together
    // handed the session back after two served reads. Bounded separately so a
    // model that never issues a native call is not fed forever.
    const served = consecutiveServedTurns < AUTO_EXEC_MAX_TURNS
      ? autoExecuteReadOnly(parsedTag, ctx.cwd)
      : null;
    if (served) {
      consecutiveServedTurns += 1;
      ctx.ui.notify(
        `🛠️ Universal Parser: served '${parsedTag.name}' for the model (${consecutiveServedTurns}/${AUTO_EXEC_MAX_TURNS})`,
        "info",
      );
      pi.sendMessage(
        {
          customType: "universal-tag-transformer",
          content:
            `[SYSTEM] 你剛才用標籤文字描述了 ${parsedTag.name}，不是原生工具呼叫。\n` +
            `系統已代為執行並取得結果（唯讀操作才會這樣處理；write/edit/bash 不會）：\n\n` +
            `--- ${parsedTag.name}: ${served.path} ---\n${served.text}\n--- end ---\n\n` +
            `請直接根據上面的結果繼續工作。下一步若還要用工具，請發出真正的原生 Function Call。`,
          display: true,
        },
        { deliverAs: "followUp", triggerTurn: true },
      );
      return;
    }

    consecutiveTransformStrikes += 1;

    if (consecutiveTransformStrikes >= 3) {
      consecutiveTransformStrikes = 0;
      ctx.ui.notify("🚨 Universal Parser auto-corrected 3 turns in a row with no real tool call — handing back to the user.", "error");
      pi.sendMessage(
        {
          customType: "loop-guard",
          content:
            // "3 次自動糾正" was false: strike 3 sends THIS message instead of a
            // correction, so the model had received two. A number stated back to
            // the model has to be one the model can verify against its own
            // context; three turns is what actually happened.
            "你已經連續 3 輪用文字描述工具呼叫，系統糾正後仍然沒有發出真正的原生 Function Call。" +
            "請停止輸出任何工具標籤或 JSON 工具描述，改用文字向使用者說明你卡住的原因與需要什麼協助。",
          display: true,
        },
        { deliverAs: "followUp", triggerTurn: true },
      );
      return;
    }

    // Describe the offending output; never reproduce it.
    //
    // This message used to quote the model's raw markup back at it under a
    // "SYSTEM CRITICAL" header. Observed consequence: the model emitted
    // `<function_calls><invoke name="web_search">`, the correction echoed that
    // XML verbatim, and the next turn emitted it again — three corrections
    // meant three fresh examples of the exact format being forbidden, sitting
    // in context. It never recovered and gave up asking the user for help.
    //
    // This repo had already learned the lesson elsewhere (87abf09 sanitised XML
    // tag instructions out of the systemPrompt); the correction path
    // reintroduced it. The parsed intent below carries everything the model
    // needs — the markup adds nothing but reinforcement.
    const shape = /<[a-z_]+[\s>]/i.test(parsedTag.raw)
      ? "XML/標籤形式"
      : /```/.test(parsedTag.raw)
        ? "Markdown 程式碼區塊形式"
        : "純文字 JSON 形式";
    const batchNote =
      parsedTag.count && parsedTag.count > 1
        ? `\n（你一次描述了 ${parsedTag.count} 個工具呼叫。請先發出第一個，其餘的在後續回合逐一發出。）`
        : "";
    // Never assert that a tool does not exist. This guard knows Pi's built-ins
    // and this harness's bridges; other extensions, packages and MCP servers
    // register tools it cannot see. Telling a model "that tool is unavailable"
    // when it was correctly asked to use it produces the contradiction
    // documented above HARNESS_TOOLS — it burned all three strikes arguing with
    // the guard instead of calling a tool that existed the whole time.
    const unknownNote = parsedTag.unknownTool
      ? `\n（'${parsedTag.name}' 不在本守衛已知的清單內。若它由某個擴充提供，照樣以原生呼叫發出即可；若你其實想用內建工具，可用的是：${[...PI_TOOLS].join(", ")}。）`
      : "";
    // Name what was thrown away. A parse the model cannot see is a parse it
    // cannot correct, and this one deletes lines from a command it is about to
    // be asked to run.
    const droppedNote =
      parsedTag.droppedLines && parsedTag.droppedLines.length
        ? `\n（下列結尾行看起來是指令的「輸出」而不是指令，已從參數中移除：${parsedTag.droppedLines
            .map((l) => `\`${l.trim()}\``)
            .join("、")}。若其中有你真正要執行的指令，請自行改回。）`
        : "";

    ctx.ui.notify(
      `🛠️ Universal Parser: transformed fake tool call into '${parsedTag.name}' (strike ${consecutiveTransformStrikes}/3)`,
      "info",
    );

    pi.sendMessage(
      {
        customType: "universal-tag-transformer",
        content:
          `[SYSTEM CRITICAL AUTO-CORRECTION]\n` +
          `偵測到你剛才以${shape}描述工具呼叫，而不是發出真正的呼叫。` +
          `（原文不在此重複，以免你再照著寫一次。）\n\n` +
          `系統已識別你的意圖為呼叫原生工具【${parsedTag.name}】，解析後的參數為：\n` +
          `${JSON.stringify(parsedTag.args, null, 2)}${batchNote}${unknownNote}${droppedNote}\n\n` +
          // The arguments above are a GUESS, produced by a regex over the
          // model's text. 【立即且只能】 left no room to decline one, and a
          // mis-parse then had a
          // direct path to bash: session 019ffbdd parsed `commit fe56ec6` — a
          // line of git OUTPUT — into a command and ordered it run. Text the
          // model merely quoted (a fenced block from a fetched web page, its own
          // transcript) reaches this same path, and nothing here asks where the
          // text came from. So the instruction now states what it is: a
          // reconstruction, to be issued if correct and corrected if not.
          `【請這樣做】：上面的參數是本守衛從你的文字「解析」出來的，不是你送出的呼叫。\n` +
          `若解析正確，請直接以原生工具 '${parsedTag.name}' 發出這個呼叫。\n` +
          `若解析不正確，請不要照著送出——改用純文字說明你原本想做什麼，或直接發出正確的原生呼叫。\n` +
          `無論哪一種，都不要再輸出 XML 標籤、\`\`\`json 工具清單或 \`\`\`bash 程式碼塊。`,
        display: true,
      },
      // MUST be "followUp", not "nextTurn". Pi's docs (docs/extensions.md) are
      // explicit: "nextTurn" is "queued for next user prompt, does not
      // interrupt or trigger anything", and `triggerTurn` is "only applied to
      // steer and followUp modes (ignored for nextTurn)".
      //
      // With "nextTurn" the correction sat in a queue until the human typed
      // again — so the transformer never auto-advanced anything. That is the
      // stall this guard exists to break: the agent emits a tag-shaped call,
      // the transformer "fires", and nothing happens until you press a key.
      // Commit 87abf09 added triggerTurn: true here believing it would take
      // effect; it was silently ignored for this delivery mode.
      //
      // Found by scripts/measure-triggers.py on its first real run: a --print
      // session emitted <tool_code> and the session ended with no correction
      // message recorded at all. The 3-strike escalation below always used
      // "followUp" and did work, which is why the failure hid — the loud path
      // functioned while the quiet, common path did not.
      { deliverAs: "followUp", triggerTurn: true }
    );
    return;
  }

  if (!cfg.enableSelfHealingLoopGuard) return;

  // Guard 6, before the markup check below: these turns carry no markup at all,
  // so looksLikeFakeToolCall returns false and resets every counter.
  //
  // Each denial is answered with the tools that answer THAT denial, and only
  // when the session actually has them. Naming the capability the model
  // declined is the whole point: the version that answered every denial with
  // the filesystem list sent a model that wanted the web to run `whoami`.
  const active = activeToolNames(pi);
  const webActive = webToolsAmong(active);
  const fsActive = localToolsAmong(active);
  const deniedFs = CAPABILITY_DENIAL.test(text) && fsActive.length > 0;
  const deniedWeb = WEB_DENIAL.test(text) && webActive.length > 0;
  const denied = deniedFs || deniedWeb;
  const fabricated = !sawAnyRealToolCall && FABRICATED_COMPLETION.test(text);
  if (denied || fabricated) {
    consecutiveFakeToolStrikes += 1;
    if (consecutiveFakeToolStrikes <= 3) {
      ctx.ui.notify(
        `🚨 Turn ended with no tool call but ${denied ? (deniedWeb ? "denied web access" : "denied filesystem access") : "claimed work it never did"} (strike ${consecutiveFakeToolStrikes}/3).`,
        "error",
      );
      pi.sendMessage(
        {
          customType: "loop-guard",
          content:
            (deniedWeb
              ? "[SYSTEM] 你剛才說你沒有網路／即時搜尋的能力，但這個 session 現在就有可用的網頁工具：" +
                `${webActive.join(", ")}。它們會真的連上網路。` +
                "\n請直接以原生 Function Call 使用它們，不要在一次都沒試過的情況下宣告做不到，" +
                "也不要改用與使用者要求無關的替代動作。"
              : deniedFs
                ? "[SYSTEM] 你剛才說沒有檔案系統存取權，但這個 session 有原生工具可用：" +
                  `${fsActive.join(", ")}。它們直接在這台機器上執行。`
                : "[SYSTEM] 你剛才宣稱已經讀取／執行了某個東西，但這個 session 到目前為止沒有任何一次真正的工具呼叫。" +
                  "不要陳述你沒有實際做過的動作。") +
            "\n請立刻發出真正的原生 Function Call 完成該動作；若你判斷不需要動作，請直接說明理由，不要宣稱做過。",
          display: true,
        },
        { deliverAs: "followUp", triggerTurn: true },
      );
    }
    return;
  }

  // Guard 7, before the reset below: these turns carry no markup either, so
  // without this branch they fall straight through to "nothing to see" and the
  // session ends silently.
  if (announcesUnfulfilledNextStep(text)) {
    if (consecutiveIntentNudges < MAX_INTENT_NUDGES) {
      consecutiveIntentNudges += 1;
      ctx.ui.notify(
        `🚨 Turn announced a next step but made no tool call (nudge ${consecutiveIntentNudges}/${MAX_INTENT_NUDGES}).`,
        "error",
      );
      pi.sendMessage(
        {
          customType: "loop-guard",
          // Deliberately does NOT quote the stalled text back. Feeding a model
          // its own broken output and asking it to act on it is how the
          // transformer produced a three-strike deadlock on 2026-07-28.
          content:
            "[SYSTEM] 你剛才描述了接下來要做的動作，但這一輪沒有發出任何工具呼叫，回合就結束了。" +
            "宣告下一步不等於執行它。\n" +
            "請立刻用原生 Function Call 執行那個動作。若那個動作其實不需要，或你需要使用者提供資訊，" +
            "請直接說明，不要以描述動作作結。",
          display: true,
        },
        { deliverAs: "followUp", triggerTurn: true },
      );
    }
    return;
  }

  if (!looksLikeFakeToolCall(text)) {
    consecutiveFakeToolStrikes = 0;
    consecutiveTransformStrikes = 0;
    consecutiveServedTurns = 0;
    return;
  }

  ctx.ui.notify(
    `🚨 Turn ended with no real tool call, but text looks like a fake tool-call tag (strike ${consecutiveFakeToolStrikes + 1}/3).`,
    "error",
  );

  consecutiveFakeToolStrikes += 1;

  if (consecutiveFakeToolStrikes >= 3) {
    consecutiveFakeToolStrikes = 0;
    pi.sendMessage(
      {
        customType: "loop-guard",
        content:
          "系統偵測到：你連續 3 次的回覆都沒有呼叫真正的工具，卻寫出了格式如 ```bash 或 <read> 的標籤文字。" +
          "請直接停止輸出標籤與程式碼塊文字。如果你原本想讀檔或執行指令，請改用真正的原生工具呼叫；如果你不確定下一步，請告訴使用者你卡住的原因。",
        display: true,
      },
      { deliverAs: "followUp", triggerTurn: true },
    );
  } else {
    // Self-healing auto-retry on strike 1 & 2 to prevent deadlocks
    pi.sendMessage(
      {
        customType: "loop-guard",
        content:
          `[System Self-Healing Auto-Retry] 提醒：這輪回覆沒有真正呼叫工具，但文字包含工具標籤或 Markdown 程式碼塊（Strike ${consecutiveFakeToolStrikes}/3）。` +
          "請重新回覆並發起標準的原生 Function Call 呼叫工具。",
        display: true,
      },
      // "followUp", not "nextTurn": this is the *auto-retry* on strikes 1 and 2.
      // Queued for the next user prompt it retries nothing on its own — the
      // agent stays stalled until a human types, which is the exact failure the
      // self-healing path exists to prevent.
      { deliverAs: "followUp", triggerTurn: true },
    );
  }
}

export default function (pi: ExtensionAPI) {
  // Pi calls this default export once per process and fires session_start once
  // per session, so a tally that is never cleared carries the previous session's
  // searches into the next one — and would refuse a query the new session has
  // not yet made.
  pi.on("session_start", async () => {
    cycleDetector.reset();
    researchDepth.reset();
    // Per-session, like the other two. A count carried between sessions would
    // show the listing on the first refusal of the next one, before the short
    // form has had its chance.
    containmentRefusals = 0;
  });

  pi.on("before_agent_start", (event, _ctx) => {
    let rawPrompt = event.systemPrompt ?? "";

    // Sanitize XML tag tool instructions introduced by third-party packages (e.g. superpowers)
    // to prevent local GGUF models from imitating XML text tags.
    rawPrompt = rawPrompt.replace(/<(?:read|write|edit|bash|ls|dir|browse|search)>\s*[\s\S]*?<\/(?:read|write|edit|bash|ls|dir|browse|search)>/gi, "");

    const systemPrompt = rawPrompt + "\n\n" +
      "============================================================\n" +
      "[CRITICAL SYSTEM PROTOCOL: NATIVE TOOL CALLING ONLY]\n" +
      "• You MUST execute all actions using native JSON function calling (tool_call).\n" +
      "• NEVER output bash commands or tool calls inside markdown code blocks (e.g. ```bash) or XML tags (<read>, <write>, <bash>, <ls>).\n" +
      "• Text code blocks and XML tags are NOT executed by the system and will cause execution to halt.\n" +
      "============================================================\n";

    // Prompt-budget measurement. Every number in docs/KNOWN_ISSUES.md's prompt
    // accounting was previously assembled by tokenizing candidate files and
    // subtracting — which assumes each file is injected at all. Dump the real
    // thing instead. Off unless the env var names a file; this runs on every
    // agent start and the prompt carries whatever the project's files carry.
    const dumpTo = process.env.PI_HARNESS_DUMP_PROMPT;
    if (dumpTo) {
      try {
        writeFileSync(dumpTo, systemPrompt, "utf-8");
      } catch {
        // Measurement must never break a session.
      }
    }

    return { systemPrompt };
  });

  pi.on("tool_call", async (event, ctx) => {
    // FIRST, before any guard reads the arguments.
    //
    // A residual dialect tag is part of the string every other guard judges:
    // session 019ffbdd produced `…/.gitignore</atem:日>` as a `path`, and
    // containment, the harness-root hint and the repeat detector would all have
    // been reasoning about a filename that the model never meant to write. The
    // repair has to happen before they look, not after.
    recordResidue(scrubToolInput(event.toolName, event.input), ctx);

    const runaway = runawayArgumentGuard(event, ctx);
    if (runaway) return runaway;
    const repeat = repeatCallGuard(event, ctx, pi);
    if (repeat) {
      ctx.ui.notify(`🔁 Blocked identical '${event.toolName}' call repeated ${REPEAT_CALL_LIMIT}×`, "warning");
      return repeat;
    }
    // The guard above is consecutive-only by design, so a loop that cycles
    // through queries resets it on every call. Measured: 598 web_searches, 43
    // distinct queries repeated ~44 times each, 25 minutes, and it stayed silent
    // throughout. See loop-detect.ts.
    const cycling = cycleDetector.check(event.toolName, event.input);
    if (cycling) {
      ctx.ui.notify(`🔁 Blocked a lookup already issued ${SAME_QUERY_LIMIT}× — same query, same answer`, "warning");
      return cycling;
    }
    // Breadth without depth, and a run that leaves nothing behind. Counts
    // web_open and write/edit too, so it must see every call, not just searches.
    const shallow = researchDepth.check(event.toolName, event.input);
    if (shallow) {
      const s = researchDepth.stats();
      ctx.ui.notify(
        `🔎 ${s.searches} 次搜尋 / 開啟 ${s.opens} 頁 / 寫入 ${s.writes} 檔 — 已擋下,請先讀或先落檔`,
        "warning",
      );
      return shallow;
    }
    if (event.toolName === "bash") {
      // Cross-shell quoting first: the destructive-pattern script has nothing to
      // say about it, and a command that cannot work should not be run at all.
      const xshell = crossShellQuotingGuard(event, ctx);
      if (xshell) return xshell;
      // Containment, which until 2026-08-06 was wired to write/edit only. A
      // live run refused there retried with `echo ... > <same path>`, got
      // through, and left a file inside this harness's vendored submodule.
      const escaped = bashContainmentBlock(
        String((event.input as { command?: unknown })?.command ?? ""), String(ctx.cwd ?? ""));
      if (escaped) {
        ctx.ui.notify("🚧 已擋下寫到專案外的 bash 指令", "warning");
        // The escalation belongs to BOTH containment paths, not just write/edit.
        //
        // Measured in T2 run 1 (session 019fedc9): two containment refusals
        // fired and the workspace listing appeared in neither, because refusal 1
        // came from containmentGuard — which counts — and refusal 2 came from
        // here, a different function with its own text and no counter. The run
        // spent all 24 calls inside the harness queue and never saw the listing
        // that exists to redirect it. The mechanism under test could not fire,
        // so that run measured nothing.
        //
        // Same omission-in-two-places shape as the `2>/dev/null` bug, this time
        // in the refusal text rather than the extractor.
        return {
          ...escaped,
          reason: withWorkspaceListing(escaped.reason, String(ctx.cwd ?? "")),
        };
      }
      return bashGuard(event, ctx);
    }
    if (event.toolName === "write" || event.toolName === "edit") return containmentGuard(event, ctx);
  });

  // Refusals reach this bridge through the execution pair, not through
  // `tool_result`.
  //
  // The second wiring watched `tool_result` on the reasoning that a refused
  // call "arrives with isError set and the reason as content, whoever refused
  // it". Measured on 2026-08-06 with a probe on the installed bridge, one run
  // per row:
  //
  //     blocked call:  tool_execution_start (args), tool_execution_end
  //                    (isError: true, reason) — no tool_call, no tool_result
  //     allowed call:  all four
  //
  // So the tracker never recorded a single block in any real session, while its
  // unit tests passed. The session transcript is what made the wrong wiring look
  // right: Pi writes a `role: toolResult` record with `isError: true` into the
  // log, and that record is not the event handlers receive.
  pi.on("tool_execution_start", async (event) => {
    blockedClaims.executionStart(event.toolCallId, event.toolName, event.args);
  });

  pi.on("tool_execution_end", async (event) => {
    blockedClaims.executionEnd(event.toolCallId, event.toolName, event.isError, event.result);
  });

  // Still `tool_result` for this one, and deliberately: it needs the tool's
  // input under a settled shape (`path`), it only cares about calls that ran,
  // and a correction pointing at a deliverable is wrong if the write was
  // refused. `tool_execution_end` fires for both outcomes and carries no input.
  pi.on("tool_result", async (event) => {
    if (event.isError === true) return;
    if (event.toolName === "write" || event.toolName === "edit") {
      const p = (event.input as { path?: unknown })?.path;
      if (typeof p === "string" && p) {
        const leaf = p.replace(/\\/g, "/").split("/").pop() as string;
        if (leaf && !turnWrites.includes(leaf)) turnWrites.push(leaf);
      }
    }
  });

  pi.on("turn_end", async (event, ctx) => {
    const finalText = extractMessageText((event as { message?: unknown }).message);

    // A reply that opens with Pi's compaction envelope when nobody compacted.
    // Session 019fd702: the work was done and a 9,092-char report written, and
    // the user read a chronological recap of the conversation instead — then
    // reasonably concluded the whole methodology had stopped working.
    // A turn that produced no text is not the end of a reply — Pi ends a turn
    // whenever the model stops, and a model that only called a tool stops with
    // nothing to say. Clearing the turn's history there is what kept the
    // blocked-claim guard silent even after its events were wired correctly:
    // the block landed in the tool-only turn and the claim arrived in the next
    // one, with an empty history behind it.
    const spoke = Boolean(String(finalText || "").trim());

    // A reply that opens with Pi's compaction envelope when nobody compacted.
    // Session 019fd702: the work was done and a 9,092-char report written, and
    // the user read a chronological recap of the conversation instead — then
    // reasonably concluded the whole methodology had stopped working.
    const echoed = spoke ? compactionEcho(finalText, turnWrites) : null;
    if (spoke) turnWrites = [];
    if (echoed) {
      ctx.ui.notify("⚠️ 回覆用了壓縮摘要的格式,不是答案", "warning");
      pi.sendMessage(
        { customType: "compaction-echo", content: echoed.message, display: true },
        { deliverAs: "followUp", triggerTurn: true },
      );
    }

    // One correction per turn from this pair. They can both match — a summary
    // that also asserts a refused change — and two followUp+triggerTurn
    // messages for one turn is two nudges the run has to reconcile. The echo
    // wins because it is the more fundamental complaint: the reply is not the
    // answer at all, so correcting a sentence inside it is beside the point.
    const correction = echoed ? null : blockedClaims.turnEnded(finalText);
    if (echoed) blockedClaims.reset();
    if (correction) {
      ctx.ui.notify("⚠️ 回覆宣稱了一項被擋下的變更", "warning");
      pi.sendMessage(
        { customType: "blocked-claim", content: correction.message, display: true },
        // followUp + triggerTurn, not nextTurn. The first draft used nextTurn on
        // the reasoning that the turn was over — and an existing test caught it,
        // correctly. nextTurn parks the correction until the human types again,
        // so the user reads the false "已完成" now and the truth later. The
        // point of this guard is that the reply should not stand.
        { deliverAs: "followUp", triggerTurn: true },
      );
    }
    return loopGuard(event as { message: unknown; toolResults?: unknown[] }, ctx, pi);
  });
}
