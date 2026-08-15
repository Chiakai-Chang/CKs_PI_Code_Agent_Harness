#!/usr/bin/env python3
"""Ask the model server what it actually loaded, before a session finds out.

Swapping a bridge has verify-bridges.py. Swapping config has validate-config.py.
Swapping the prompt has check-prompt-conflicts.py. Swapping the MODEL had
docs/retro/2026-07-29-model-swap-checklist.md — a markdown file somebody has to
remember to read. On 2026-08-13 nobody did, and the cost was a 6.5-hour session
in which every file the model wrote ended in `</atem:日>`.

What that was: the served chat template renders assistant tool calls as

    <atem:function_calls>
    <atem:invoke name="write">
    <atem:parameter name="content">…</atem:parameter>
    </atem:invoke>
    </atem:function_calls>

and its tool-definition block teaches the model to emit exactly that. Pi drives
the model with native OpenAI `tool_calls` instead. Two tool-call protocols, one
model: the model closed its last parameter the way its template taught it, and
`</atem:parameter>` — mangled in decoding to `</atem:日>` — landed inside the
argument value. 24 times in one session, once inside a `path`, and 20 files in
the project the owner was working in still carry it.

llama.cpp does not report any of this. It silently prefers the GGUF's embedded
template when `--chat-template-file` cannot be honoured — including whenever
`--mmproj` is present (ggml-org/llama.cpp#24189), which is exactly this machine's
configuration.

WHAT THIS SCRIPT DOES NOT DO: change anything. The repo ships no model default —
which model is served, and with which template, is this machine's calibration and
the operator's decision. This reports a mismatch and names it; the fix is a
server restart the operator makes.

    python scripts/check-model-serving.py
    python scripts/check-model-serving.py --url http://127.0.0.1:8080 --expect-model muse-glimmer
    python scripts/check-model-serving.py --template <file>     # offline, no server

Exit 0 when consistent or when no server is listening (SKIP, same semantics as
verify-bridges.py's drift check). Exit 1 on a mismatch.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "pi-config", "serving-check-report.json")
DEFAULT_URL = "http://127.0.0.1:8080"

# Tool-call dialects a chat template can teach, and whether the SERVER can read
# that dialect back. Each entry is (name, pattern, parseable).
#
# The namespace prefix is part of the pattern and not an afterthought: the
# harness's own FAKE_TOOL_CALL_PATTERN matched `<invoke` and `<parameter name=`
# and therefore did not match `<atem:invoke` or `<atem:parameter name=`. A
# dialect slipped past every detector in the repo because of a prefix.
#
# `parseable` is the half this script got wrong on its first real use. The first
# version failed any template that taught a dialect, on the reasoning that Pi
# drives the model with native OpenAI tool_calls. Then a model swap to
# Qwen3.8-27B produced a template that teaches
# `<tool_call><function=name><parameter=key>` — and a live probe returned
# `finish_reason: tool_calls` with structured arguments and empty content,
# because llama.cpp HAS a parser for that shape and converts it back. Teaching a
# dialect is not the defect. Teaching one nothing can read back is.
#
# llama.cpp ships parsers for the qwen/hermes/deepseek family. It ships none for
# the Anthropic-style `<function_calls>/<invoke>/<parameter>` shape, which is the
# one that produced `</atem:日>` inside 24 arguments on 2026-08-13.
DIALECTS = [
    ("anthropic-style XML", re.compile(r"<(?:[A-Za-z][\w.-]*:)?function_calls>"), False),
    ("anthropic-style XML", re.compile(r"<(?:[A-Za-z][\w.-]*:)?invoke\s+name="), False),
    ("anthropic-style XML", re.compile(r"<(?:[A-Za-z][\w.-]*:)?parameter\s+name="), False),
    ("qwen-style <tool_call>", re.compile(r"<(?:[A-Za-z][\w.-]*:)?tool_call>"), True),
    ("qwen-style <function=>", re.compile(r"<function="), True),
    ("hermes-style <tools>", re.compile(r"<(?:[A-Za-z][\w.-]*:)?tools>"), True),
]

# Emitting the dialect is what matters. A template that only RENDERS one —
# putting a past tool call back into the conversation — is doing its job.
#
# The alternation grew on first contact with a second model. The original had
# only the "you can/should/must invoke…" family and read the Qwen3.8 template as
# not teaching anything, while that template says outright:
#
#   If you choose to call a function ONLY reply in the following format …
#   <IMPORTANT> Function calls MUST follow the specified format …
#
# A heuristic over prose will keep missing phrasings; that is why the live probe
# below exists and why this is one input to the verdict rather than the verdict.
TEACHES = re.compile(
    r"you (?:can|should|must) (?:invoke|call|use)[^\n]{0,80}(?:function|tool)"
    r"|by writing a"
    r"|write a \"?<"
    r"|reply in the following format"
    r"|(?:must|should) follow the specified format"
    r"|respond with a[^\n]{0,40}(?:function|tool)[ _-]?call", re.I)


def fetch_props(url, timeout=10):
    """The server's own account of what it loaded. None when nothing answers."""
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/props", timeout=timeout) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def completions_ready(url, timeout=10):
    """Checklist §1: while a model loads, /props answers and
    /v1/chat/completions returns 503. Measuring before this is 200 measures the
    loader, not the model."""
    body = json.dumps({"messages": [{"role": "user", "content": "ping"}],
                       "max_tokens": 1}).encode()
    req = urllib.request.Request(
        url.rstrip("/") + "/v1/chat/completions", data=body,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return None, str(e)


def find_dialects(template):
    """Which tool-call dialects this template speaks, and the tags proving it.

    Returns [(dialect_name, [tag, ...])] sorted by name, so the report names what
    was found rather than asserting that something was."""
    if not template:
        return []
    found = {}
    for name, pat, _parseable in DIALECTS:
        for m in pat.finditer(template):
            found.setdefault(name, set()).add(m.group(0))
    return sorted((n, sorted(t)) for n, t in found.items())


PARSEABLE = {name: ok for name, _pat, ok in DIALECTS}

# Residue as it appears INSIDE an argument value, which is a different shape from
# a dialect in a template. A template shows opening tags (`<atem:invoke name=`);
# what survives into an argument is the CLOSING tag the model appended when it
# finished the parameter — `</atem:parameter>`, or the mangled `</atem:日>` that
# was actually measured. Reusing find_dialects here silently matched nothing.
RESIDUE_IN_VALUE = re.compile(
    r"</(?:[A-Za-z][\w.-]*:)?(?:parameter|invoke|function_calls|function|tool_call)\s*>"
    r"|</[A-Za-z][\w.-]*:[^<>\s]{0,24}>")


def unparseable_dialects(dialects):
    """The ones no server-side parser reads back. This is the distinction the
    first version of this script did not draw, and drawing it is what separates
    the Qwen template (teaches a dialect llama.cpp converts to real tool_calls)
    from the ATEM one (teaches a dialect nothing converts, so its closing tags
    land inside argument values)."""
    return [n for n, _tags in dialects if not PARSEABLE.get(n, True)]


def probe_tool_call(url, timeout=180):
    """Offer one tool and see whether a real tool call comes back.

    The decisive question this whole script exists for is not what the template
    says; it is whether THIS configuration produces native tool calls. A
    heuristic over jinja prose cannot answer that and has already been wrong
    once. One request can.

    Returns a dict, or None when the server cannot be reached — never raises, so
    a slow or absent server degrades to "not probed" rather than to a failure.
    """
    body = {
        "messages": [{"role": "user", "content": "Read the file README.md. Use the tool."}],
        "tools": [{"type": "function", "function": {
            "name": "read", "description": "Read a file",
            "parameters": {"type": "object",
                           "properties": {"path": {"type": "string"}},
                           "required": ["path"]}}}],
        "tool_choice": "auto", "max_tokens": 200, "temperature": 0,
    }
    req = urllib.request.Request(
        url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
    except Exception as exc:  # noqa: BLE001 - any transport failure means "not probed"
        return {"error": str(exc)[:200]}
    try:
        choice = data["choices"][0]
        msg = choice.get("message") or {}
    except (KeyError, IndexError, TypeError):
        return {"error": "unexpected response shape"}
    calls = msg.get("tool_calls") or []
    return {
        "finish_reason": choice.get("finish_reason"),
        "native_tool_calls": len(calls),
        "arguments": [c.get("function", {}).get("arguments") for c in calls][:3],
        "content_head": (msg.get("content") or "")[:400],
    }


def teaches_dialect(template):
    """Whether the template instructs the model to WRITE the dialect, as opposed
    to only rendering it back."""
    return bool(template) and bool(TEACHES.search(template))


def assess(props, template=None, expect_model=None, completions_status=None,
           probe=None):
    """The whole judgement, as data. No I/O, so a test can drive every branch."""
    props = props or {}
    template = template if template is not None else props.get("chat_template", "")
    dialects = find_dialects(template)
    teaches = teaches_dialect(template)

    out = {
        "model_path": props.get("model_path"),
        "model_alias": props.get("model_alias"),
        "modalities": props.get("modalities"),
        "template_sha256": hashlib.sha256(
            (template or "").encode("utf-8")).hexdigest() if template else None,
        "template_bytes": len((template or "").encode("utf-8")),
        "dialects": [{"name": n, "tags": t} for n, t in dialects],
        "teaches_dialect": teaches,
        "completions_status": completions_status,
        "probe": probe,
        "failures": [],
        "warnings": [],
    }

    unreadable = unparseable_dialects(dialects)
    out["unparseable_dialects"] = unreadable

    if unreadable and teaches:
        tags = sorted({t for n, ts in dialects if n in unreadable for t in ts})
        out["failures"].append(
            "the chat template teaches the model to emit tool calls as "
            + ", ".join(unreadable)
            + " (" + ", ".join(tags[:6]) + "), and no server-side parser reads "
            "that shape back. The model will close its last argument with the "
            "dialect's closing tag and that text lands INSIDE the argument "
            "value — in `path` it produces ENOENT, in `content` it is written to "
            "disk. Serve a template whose tool-call protocol matches, and note "
            "that llama-server ignores --chat-template-file when --mmproj is "
            "present (llama.cpp#24189).")
    elif dialects and teaches:
        out["warnings"].append(
            "the chat template teaches a tool-call dialect ("
            + ", ".join(n for n, _ in dialects)
            + "), which is normal when the server parses that shape back into "
              "real tool_calls — llama.cpp does for the qwen/hermes family. The "
              "probe below is what confirms it actually happens.")
    elif dialects:
        out["warnings"].append(
            "the chat template mentions a tool-call dialect ("
            + ", ".join(n for n, _ in dialects)
            + ") but does not appear to instruct the model to write one. "
              "Rendering a dialect back is normal; emitting it is not.")

    # The probe outranks every heuristic above. A jinja template is prose; this
    # is the configuration answering the actual question.
    probe = out.get("probe")
    if probe and not probe.get("error"):
        if not probe.get("native_tool_calls"):
            head = (probe.get("content_head") or "").strip()
            out["failures"].append(
                "offered one tool and the server returned no native tool_calls "
                "(finish_reason %r). Pi cannot execute anything this "
                "configuration produces.%s"
                % (probe.get("finish_reason"),
                   (" It replied with text instead, beginning: %r" % head[:160])
                   if head else ""))
        else:
            residue = [a for a in (probe.get("arguments") or [])
                       if a and RESIDUE_IN_VALUE.search(a)]
            if residue:
                out["failures"].append(
                    "a native tool call came back, but its arguments still carry "
                    "dialect markup (%r). That text is what reaches the "
                    "filesystem." % residue[0][:160])

    # Multimodal is not a defect. It is the documented trigger for the silent
    # fallback, so it is worth saying out loud next to a dialect finding.
    if (props.get("modalities") or {}).get("vision") and dialects:
        out["warnings"].append(
            "mmproj is loaded (modalities.vision), which is when llama-server "
            "silently ignores --chat-template-file — so the template above may "
            "not be the one the launch command names.")

    if expect_model:
        got = " ".join(str(props.get(k) or "")
                       for k in ("model_path", "model_alias"))
        if expect_model.lower() not in got.lower():
            out["failures"].append(
                "expected a model matching %r, server reports %r"
                % (expect_model, got.strip()))

    if completions_status is not None and completions_status != 200:
        out["failures"].append(
            "/v1/chat/completions returned %s, not 200. While a model loads, "
            "/props answers and this does not; anything measured now measures "
            "the loader." % completions_status)

    return out


def write_report(result, path=REPORT):
    """Same shape as skill-conflict-report.json: the notify is gone when the
    session ends, the file is what survives."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default=os.environ.get("PI_MODEL_URL", DEFAULT_URL))
    ap.add_argument("--expect-model", default=None,
                    help="substring the served model_path/alias must contain")
    ap.add_argument("--template", default=None,
                    help="read a template from a file instead of a server")
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--no-probe", action="store_true",
                    help="skip the live tool-call round trip (it costs one "
                         "generation; the heuristics alone have been wrong)")
    args = ap.parse_args(argv)

    if args.template:
        with open(args.template, encoding="utf-8") as f:
            template = f.read()
        result = assess({}, template=template, expect_model=args.expect_model)
        result["source"] = args.template
    else:
        props = fetch_props(args.url)
        if props is None:
            print("SKIP: nothing answered at %s/props — start the model server "
                  "before believing this check." % args.url.rstrip("/"))
            return 0
        status, _err = completions_ready(args.url)
        probe = None if args.no_probe else probe_tool_call(args.url)
        result = assess(props, expect_model=args.expect_model,
                        completions_status=status, probe=probe)
        result["source"] = args.url

    print("Source: %s" % result["source"])
    if result.get("model_path"):
        print("Model:  %s" % result["model_path"])
    print("Template: %d bytes, sha256 %s"
          % (result["template_bytes"], (result["template_sha256"] or "-")[:16]))
    for d in result["dialects"]:
        readable = "" if PARSEABLE.get(d["name"], True) else "  [no parser reads this back]"
        print("  dialect: %s -> %s%s" % (d["name"], ", ".join(d["tags"][:4]), readable))
    p = result.get("probe")
    if p:
        if p.get("error"):
            print("  probe: not run (%s)" % p["error"])
        else:
            print("  probe: finish_reason=%s, native tool_calls=%d, args=%s"
                  % (p.get("finish_reason"), p.get("native_tool_calls") or 0,
                     (p.get("arguments") or [None])[0]))
    for w in result["warnings"]:
        print("WARN: %s" % w)
    for f in result["failures"]:
        print("FAIL: %s" % f)

    write_report(result, args.report)
    print("\nModel serving check complete: %d failure(s), %d warning(s)."
          % (len(result["failures"]), len(result["warnings"])))
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
