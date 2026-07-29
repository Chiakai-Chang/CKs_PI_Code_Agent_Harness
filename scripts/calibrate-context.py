#!/usr/bin/env python3
"""Measure this machine's usable context, and write it to the local override.

Why this exists instead of a shipped constant: the point where a model stops
calling tools and starts fabricating depends on the model, the quantization, the
inference engine and the installed skill set. On the machine this was developed
on, a 27B Q6_K scored 8/8 clean at 20,100 prompt tokens and 6/8 at 23,083 — but
that number is a property of that setup, not of the harness. Shipping it would
be the same mistake as hardcoding a machine's paths into a template.

So the harness ships the measurement, not the measurement's result.

What it writes (pi-config/harness-config.local.json, gitignored):

    perTurnPromptTokens  the fixed system prompt + tool schemas, measured by
                         dumping what Pi actually sends
    usableContextTokens  the largest ladder rung that came back fully clean,
                         only when a local model was probed

restore.py turns those into models.json's contextWindow and settings.json's
compaction settings, so compaction fires while the model still works instead of
at the engine's -c value.

Usage:
    python scripts/calibrate-context.py                 # measure, print, write nothing
    python scripts/calibrate-context.py --write         # measure and write the local file
    python scripts/calibrate-context.py --ladder --write # also probe for the ceiling (slow)

Skips cleanly when there is no local server: users on hosted models do not need
a ceiling, and an unset ceiling changes nothing.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCAL_CONFIG = os.path.join(REPO_ROOT, "pi-config", "harness-config.local.json")
DEFAULT_RUNGS = [14000, 17000, 20000, 23000, 26000]
LADDER_REPEATS = 8


def log(msg):
    print(f"[CALIBRATE] {msg}")


def estimate_tokens(text):
    """Pi's own fallback heuristic (chars/4), used when no tokenizer is reachable.

    Deliberately the same rule Pi uses to estimate untokenized messages, so the
    number we write and the number Pi compares against do not disagree.
    """
    return (len(text) + 3) // 4


def tokenize_via_server(text, base_url):
    """Exact token count from a llama.cpp-compatible /tokenize endpoint.

    Returns None on any failure — a missing or different server is the normal
    case for hosted models, not an error.
    """
    try:
        req = urllib.request.Request(
            base_url.rstrip("/") + "/tokenize",
            data=json.dumps({"content": text}).encode("utf-8"),
            headers={"content-type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return len(json.load(resp).get("tokens") or [])
    except Exception:
        return None


def count_tokens(text, base_url):
    exact = tokenize_via_server(text, base_url) if base_url else None
    if exact is not None:
        return exact, "tokenizer"
    return estimate_tokens(text), "chars/4 estimate"


def local_base_url():
    """The first localhost provider in models.json, if any."""
    for path in (os.path.join(REPO_ROOT, "pi-config", "models.json"),
                 os.path.join(os.path.expanduser("~"), ".pi", "agent", "models.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        for provider in (data.get("providers") or {}).values():
            base = provider.get("baseUrl") or ""
            if "127.0.0.1" in base or "localhost" in base:
                return base
    return None


def measure_per_turn_prompt(base_url):
    """Run Pi once with the dump hook and count what it actually sent.

    Uses the real binary and the real config, because every attempt to compute
    this by adding up candidate files got it wrong: CLAUDE.md turned out to be
    injected and skill-catalog.json turned out not to be.
    """
    pi = shutil.which("pi")
    if not pi:
        log("pi not on PATH — cannot measure the per-turn prompt.")
        return None
    dump = os.path.join(tempfile.gettempdir(), "pi-harness-prompt-dump.txt")
    try:
        os.remove(dump)
    except OSError:
        pass
    env = dict(os.environ, PI_HARNESS_DUMP_PROMPT=dump)
    try:
        subprocess.run([pi, "--print", "Reply with exactly: OK"], env=env, cwd=REPO_ROOT,
                       capture_output=True, timeout=600)
    except Exception as e:
        log(f"pi run failed: {e}")
        return None
    # Prefer Pi's own accounting: the session records the real input size, which
    # includes the tool schemas sent alongside the system prompt. The dump only
    # holds the system prompt, so using it alone understates the floor by
    # whatever the tool definitions weigh (~2.9k tokens on the dev machine).
    billed = per_turn_from_session()
    if billed:
        log(f"per-turn input: {billed} tokens (Pi's own usage accounting, includes tool schemas)")
        return billed

    if not os.path.exists(dump):
        log("no dump produced — is yes-hooks-bridge installed? run: python scripts/setup.py --mode restore")
        return None
    with open(dump, encoding="utf-8") as f:
        prompt = f.read()
    tokens, how = count_tokens(prompt, base_url)
    log(f"per-turn system prompt: {tokens} tokens ({how}, {len(prompt)} chars)")
    log("  note: tool schemas are not in the dump, so this understates the real floor")
    return tokens


def per_turn_from_session():
    """First assistant usage from the newest session for this directory.

    `input + cacheRead` is what the request actually cost, so it counts the
    system prompt, the tool schemas and the user turn together — the floor that
    is present in every turn and that compaction cannot remove.
    """
    root = os.path.join(os.path.expanduser("~"), ".pi", "agent", "sessions")
    newest, newest_mtime = None, -1
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".jsonl"):
                continue
            path = os.path.join(dirpath, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime > newest_mtime:
                newest, newest_mtime = path, mtime
    if not newest:
        return None
    try:
        with open(newest, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                usage = ((entry.get("message") or {}).get("usage")) or {}
                total = (usage.get("input") or 0) + (usage.get("cacheRead") or 0)
                if total:
                    return total
    except Exception:
        return None
    return None


def run_ladder(base_url, rungs, repeats):
    """Probe each rung and return [(size, clean, total)].

    Padding is unrelated filler so that only size varies; measured on the dev
    machine, repo documentation and neutral filler of the same token count gave
    identical results, so the content does not matter but the size does.
    """
    probe = os.path.join(REPO_ROOT, "scripts", "probe-tool-calls.mjs")
    node = shutil.which("node")
    if not node or not os.path.exists(probe):
        log("node or probe-tool-calls.mjs missing — skipping the ladder.")
        return []
    filler_unit = (
        "## Ledger revision notes\n\nThis revision adjusts the column ordering of the "
        "settlement table and clarifies how partial reconciliations are recorded when a "
        "counterparty submits an amended statement after the cut-off. Implementers "
        "reported that the previous ordering made streaming parsers allocate an "
        "intermediate buffer for the trailing checksum.\n\n"
    )
    results = []
    for target in rungs:
        body = ""
        while True:
            candidate = body + filler_unit
            tokens, _ = count_tokens(candidate, base_url)
            if tokens > target:
                break
            body = candidate
        path = os.path.join(tempfile.gettempdir(), f"pi-harness-rung-{target}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        size, _ = count_tokens(body, base_url)
        proc = subprocess.run([node, probe, "--system", path, "--repeats", str(repeats),
                               "--tools", "13", "--json"],
                              capture_output=True, text=True, cwd=REPO_ROOT, timeout=3600)
        try:
            data = json.loads(proc.stdout)
            clean, total = int(data["clean"]), int(data["total"])
        except Exception:
            log(f"  rung {size}: probe produced no usable output — skipped")
            continue
        log(f"  rung {size}: {clean}/{total} clean")
        results.append((size, clean, total))
    return results


def write_local(values):
    """Merge into the local override without disturbing other keys."""
    existing = {}
    if os.path.exists(LOCAL_CONFIG):
        try:
            with open(LOCAL_CONFIG, encoding="utf-8") as f:
                existing = json.load(f) or {}
        except Exception:
            existing = {}
    existing.update(values)
    existing.setdefault(
        "_comment",
        "Machine-specific overrides written by scripts/calibrate-context.py. Gitignored on purpose.")
    with open(LOCAL_CONFIG, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
        f.write("\n")
    log(f"wrote {LOCAL_CONFIG}")


def main():
    ap = argparse.ArgumentParser(description="Measure this machine's usable context window.")
    ap.add_argument("--write", action="store_true", help="write pi-config/harness-config.local.json")
    ap.add_argument("--ladder", action="store_true",
                    help="probe a size ladder to find the usable ceiling (slow, needs a local model)")
    ap.add_argument("--repeats", type=int, default=LADDER_REPEATS)
    ap.add_argument("--rungs", type=str, default=",".join(str(r) for r in DEFAULT_RUNGS))
    args = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import restore  # suggest_usable_ceiling lives with the code that consumes it

    base = local_base_url()
    log(f"local server: {base or 'none found (hosted model?)'}")

    values = {}
    per_turn = measure_per_turn_prompt(base)
    if per_turn:
        values["perTurnPromptTokens"] = per_turn

    if args.ladder:
        if not base:
            log("no local server — a usable ceiling only means something for a local model. Skipping.")
        else:
            rungs = [int(r) for r in args.rungs.split(",") if r.strip()]
            log(f"probing {len(rungs)} rungs x {args.repeats} runs (this takes a while)")
            ladder = run_ladder(base, rungs, args.repeats)
            ceiling = restore.suggest_usable_ceiling(ladder)
            if ceiling:
                log(f"usable ceiling: {ceiling} tokens (largest fully clean rung)")
                values["usableContextTokens"] = ceiling
            else:
                log("no rung came back fully clean — leaving usableContextTokens unset.")
                log("that means even the smallest rung tested is already degraded; try smaller rungs.")

    if per_turn and values.get("usableContextTokens"):
        warning = restore.compaction_headroom_warning(values["usableContextTokens"], per_turn)
        if warning:
            log(f"! {warning}")

    if not values:
        log("nothing measured; nothing to write.")
        return 1
    if args.write:
        write_local(values)
        log("run `python scripts/setup.py --mode restore` to apply.")
    else:
        log("measured (not written; pass --write):")
        log(json.dumps(values, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
