/**
 * stealth-web Bridge Extension
 *
 * Exposes the camofox-stealth recon backend as first-class, LLM-callable tools
 * (`web_search`, `web_open`) so the model reaches for them reflexively — the way
 * weak local models grabbed the old `ctx_fetch_and_index` tool — instead of
 * having to *decide* to read a passive SKILL.md. A plain skill loses to a
 * one-click function on small models; this makes stealth browsing a function.
 *
 * The tools drive the pinned local Camoufox server (127.0.0.1:9377) directly via
 * node fetch (proper UTF-8 JSON, no curl/shell mangling). Search goes through the
 * DuckDuckGo HTML endpoint (bot-friendly); Google's macro path hits /sorry.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const SERVER = process.env.STEALTH_RECON_URL || "http://127.0.0.1:9377";
const USER = "recon";
const SESSION = "r1";

// Anti-bot / challenge markers — mirror recon.sh is_blocked so a challenge page
// is never returned to the model as if it were real content.
const BLOCK_MARKERS =
  /Just a moment|Attention Required|cf-mitigated|__cf_chl|Enable JavaScript and cookies to continue|Checking your browser|detected unusual traffic|\/sorry\/index|not a robot/i;

function harnessRoot(): string {
  // pi-harness.root is patched to the absolute repo path by scripts/restore.py.
  const here = dirname(fileURLToPath(import.meta.url));
  try {
    const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf-8"));
    if (pkg["pi-harness"]?.root) return pkg["pi-harness"].root;
  } catch {}
  return join(here, "../.."); // dev fallback
}

function reconScript(): string {
  return join(harnessRoot(), "pi-skills/optional/camofox-stealth/recon.sh");
}

function loginScript(): string {
  return join(harnessRoot(), "pi-skills/optional/camofox-stealth/scripts/stealth_login.py");
}

// Run a stealth_login.py subcommand. Password (when present) is written to the
// child's stdin — never argv (which shows in process listings) and never the
// model. Returns exit code + captured stderr for the caller to report.
function runLogin(subArgs: string[], stdinData?: string): Promise<{ code: number; out: string; err: string }> {
  return new Promise((resolve) => {
    const proc = spawn("python", [loginScript(), ...subArgs], {
      timeout: 60_000,
      stdio: ["pipe", "pipe", "pipe"],
    });
    let out = "";
    let err = "";
    proc.stdout.on("data", (d: Buffer) => (out += d.toString()));
    proc.stderr.on("data", (d: Buffer) => (err += d.toString()));
    proc.on("error", (e) => resolve({ code: -1, out, err: err + String(e) }));
    proc.on("exit", (code) => resolve({ code: code ?? -1, out: out.trim(), err: err.trim() }));
    if (stdinData !== undefined) {
      proc.stdin.write(stdinData);
    }
    proc.stdin.end();
  });
}

async function serverHealthy(): Promise<boolean> {
  try {
    const r = await fetch(`${SERVER}/health`, { signal: AbortSignal.timeout(2000) });
    return r.ok;
  } catch {
    return false;
  }
}

/** Start the pinned Camoufox server via recon.sh if it is not already up. */
function ensureServer(): Promise<{ ok: boolean; log: string }> {
  return new Promise((resolve) => {
    serverHealthy().then((up) => {
      if (up) return resolve({ ok: true, log: "" });
      // First run downloads the ~300MB engine; give it room. Detached start.
      const proc = spawn("sh", [reconScript(), "ensure"], {
        timeout: 600_000,
        stdio: ["ignore", "pipe", "pipe"],
      });
      let err = "";
      proc.stderr.on("data", (d: Buffer) => (err += d.toString()));
      proc.on("exit", async () => resolve({ ok: await serverHealthy(), log: err.slice(-600) }));
      proc.on("error", (e) => resolve({ ok: false, log: String(e) }));
    });
  });
}

async function createTab(url: string): Promise<string | null> {
  const r = await fetch(`${SERVER}/tabs`, {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({ userId: USER, sessionKey: SESSION, url }),
    signal: AbortSignal.timeout(30_000),
  });
  const j: any = await r.json().catch(() => ({}));
  return j.tabId ?? null;
}

/** Poll the accessibility-tree snapshot until it has real content or times out. */
async function snapshot(tabId: string, minChars = 400, tries = 6): Promise<string> {
  let last = "";
  for (let i = 0; i < tries; i++) {
    await new Promise((res) => setTimeout(res, 1500));
    try {
      const r = await fetch(`${SERVER}/tabs/${tabId}/snapshot?userId=${USER}`, {
        signal: AbortSignal.timeout(15_000),
      });
      const j: any = await r.json().catch(() => ({}));
      last = j.snapshot ?? "";
      if (last.length >= minChars) return last;
    } catch {}
  }
  return last;
}

function toolError(text: string) {
  return { content: [{ type: "text" as const, text }], isError: true };
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "web_search",
    label: "Web Search",
    description:
      "Search the live web via a stealth browser (Camoufox) and return result titles, snippets, and URLs. Use this whenever you need current/external information: news, docs, library/API usage, other people's approaches. Routes through DuckDuckGo so bot walls (Cloudflare, Google /sorry) do not block it.",
    promptSnippet:
      "web_search(query): search the live web through a stealth browser; use for any current/external info instead of claiming you cannot go online.",
    promptGuidelines: [
      "You CAN access the internet: call web_search for any task needing current or external information. Never say you cannot browse.",
      "web_search returns only titles/snippets — that is NOT enough to analyze or answer accurately. After searching, call web_open on the 1-3 most relevant result URLs to read the full articles.",
      "web_open goes through the same stealth browser, so it reads pages that block plain fetch (Cloudflare, JS-rendered, soft paywalls). Prefer it over giving up on a source.",
    ],
    parameters: Type.Object({
      query: Type.String({ description: "The search query, e.g. '矢板明夫 案件 最新'" }),
    }),
    async execute(_id, params, _signal, _onUpdate, _ctx) {
      const ready = await ensureServer();
      if (!ready.ok) {
        return toolError(
          `Stealth browser backend failed to start. Last log:\n${ready.log || "(none)"}\nDo not fabricate results; tell the user the recon backend is down.`,
        );
      }
      const url = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(params.query)}`;
      const tabId = await createTab(url);
      if (!tabId) return toolError("Could not open a browser tab for the search.");
      const snap = await snapshot(tabId);
      if (!snap) return toolError("Search returned no snapshot; the page may not have loaded.");
      if (BLOCK_MARKERS.test(snap)) {
        return toolError(
          "The search source blocked automated access. Do not treat this as content; try a different query or source.",
        );
      }
      return {
        content: [{ type: "text" as const, text: snap }],
        details: { query: params.query, url },
      };
    },
  });

  pi.registerTool({
    name: "web_open",
    label: "Web Open",
    description:
      "Open a specific URL in the stealth browser (Camoufox) and return its readable content as an accessibility-tree snapshot (~90% smaller than raw HTML). This IS the camofox stealth reader: its C++-level fingerprint spoofing reads pages that block plain HTTP fetch — Cloudflare, JS-rendered SPAs, soft paywalls, bot walls. Use to read the full article behind any web_search result, or any URL the user gives. (Hard login walls needing real credentials/2FA are the exception — those need the /browse VNC handoff, not this tool.)",
    promptSnippet:
      "web_open(url): read a full/bot-protected web page through the stealth browser (Cloudflare, JS, soft paywalls).",
    parameters: Type.Object({
      url: Type.String({ description: "The absolute URL to open, e.g. https://example.com/article" }),
    }),
    async execute(_id, params, _signal, _onUpdate, _ctx) {
      const ready = await ensureServer();
      if (!ready.ok) {
        return toolError(
          `Stealth browser backend failed to start. Last log:\n${ready.log || "(none)"}\nDo not fabricate content.`,
        );
      }
      const tabId = await createTab(params.url);
      if (!tabId) return toolError(`Could not open a tab for ${params.url}.`);
      const snap = await snapshot(tabId, 200);
      if (!snap) return toolError("Page returned no snapshot; it may not have loaded.");
      if (BLOCK_MARKERS.test(snap)) {
        return toolError(
          `${params.url} blocked automated access. Do not treat this as content; report honestly or try another source.`,
        );
      }
      return {
        content: [{ type: "text" as const, text: snap }],
        details: { url: params.url },
      };
    },
  });

  // /login <domain> — establish a logged-in session for a site behind an auth
  // wall. Tries cookie reuse first (copies the login you already have in your
  // browser; no password). Falls back to credentials entered in a dialog —
  // stored in the OS keychain, piped over stdin, NEVER in the chat/model.
  pi.registerCommand("login", {
    description: "Log into a site for stealth browsing: reuse browser cookies, or enter credentials (kept in the OS keychain, never the chat).",
    handler: async (args, ctx) => {
      const domain = (args || "").trim();
      if (!domain) {
        ctx.ui.notify("Usage: /login <domain>   e.g. /login example.com", "warning");
        return;
      }
      const ready = await ensureServer();
      if (!ready.ok) {
        ctx.ui.notify("Stealth backend failed to start; cannot log in.", "error");
        return;
      }

      // 1. Cookie reuse — the reliable, password-free path.
      const cookies = await runLogin(["cookies", domain]);
      if (cookies.code === 0) {
        ctx.ui.notify(cookies.out || `Logged into ${domain} via browser cookies.`, "info");
        return;
      }

      // 2. Credential fallback (opt-in, out-of-model).
      const missingDep = /not installed/.test(cookies.err);
      const reason = missingDep
        ? `${cookies.err}\n\n`
        : `No reusable browser cookies for ${domain} (log in there in Firefox first, or continue with credentials).\n\n`;
      const useCreds = await ctx.ui.confirm(
        "Enter credentials?",
        `${reason}Credentials go into the OS keychain and are typed straight into the login form — they never enter the chat or the model. Sites with captcha/2FA will still fail (headless has no UI). Continue?`,
      );
      if (!useCreds) {
        ctx.ui.notify("Login cancelled. Tip: logging into the site in Firefox, then /login again, is the simplest path.", "info");
        return;
      }
      const username = await ctx.ui.input(`Username / email for ${domain}`);
      if (!username) { ctx.ui.notify("Login cancelled (no username).", "info"); return; }
      const password = await ctx.ui.input(`Password for ${domain} (stored in keychain, not shown to the model)`);
      if (!password) { ctx.ui.notify("Login cancelled (no password).", "info"); return; }
      const loginUrl = await ctx.ui.input("Login page URL", `https://${domain}/login`);
      if (!loginUrl) { ctx.ui.notify("Login cancelled (no login URL).", "info"); return; }

      const stored = await runLogin(["store", domain, username], password + "\n");
      if (stored.code !== 0) {
        ctx.ui.notify(`Could not store credentials: ${stored.err || stored.out}`, "error");
        return;
      }
      const filled = await runLogin(["fill", domain, loginUrl]);
      ctx.ui.notify(
        filled.code === 0
          ? (filled.out || `Submitted login for ${domain}. Verify with web_open.`)
          : `Login form step failed: ${filled.err || filled.out}`,
        filled.code === 0 ? "info" : "warning",
      );
    },
  });
}
