#!/usr/bin/env python3
"""Audit the prompt text every bridge injects, as a whole.

Nine bridges each inject confident instructions into the same system prompt, and
until now nothing ever looked at the combination. That gap produced two measured
failures on 2026-07-28:

  * stealth-web-bridge told the model, unconditionally, to "call web_search for
    any task needing current or external information". The model then
    web_searched for a LOCAL skill file whose path it had just read out of
    skill-catalog.json.
  * The same line beat an explicit user instruction: told "Call the
    deep_research tool once", the model called web_search instead.

Neither is a model defect. Both are one bridge's guidance claiming a scope that
swallows another bridge's tool.

WHAT THIS CAN AND CANNOT DO
---------------------------
It cannot prove two instructions conflict — that is a semantic question. What it
can do is surface the exact shapes that caused the failures above, and print the
combined injected text so a human can read what the model actually receives,
which is the feedback loop that was missing entirely:

  1. FAIL  absolutist scope claims in tool guidance ("for any task", "always
           call", "whenever you need") — the proven defect shape.
  2. WARN  two different tools claiming the same trigger vocabulary.
  3. INFO  per-bridge injected character budget.

Usage:
  python scripts/check-prompt-conflicts.py [--root DIR] [--show]
"""
import argparse
import os
import re
import sys

# Absolutist scope language. Guidance that claims "any"/"every"/"always" leaves
# no room for a more specific tool to win, which is precisely how web_search
# captured calls that belonged to deep_research and to plain file reads.
ABSOLUTE_PATTERNS = [
    (r"\bfor any (?:task|question|request|need)", 'claims "for any task/question" — no other tool can ever be more appropriate'),
    (r"\balways call\b", 'says "always call" — leaves no case for another tool'),
    (r"\bfor all (?:tasks|questions|requests)\b", 'claims "for all tasks"'),
    (r"\bwhenever you need\b(?!.{0,60}\b(?:instead|unless|except|prefer)\b)", 'says "whenever you need" with no carve-out'),
    (r"\bevery time\b(?!.{0,60}\b(?:instead|unless|except)\b)", 'says "every time" with no carve-out'),
]

# Vocabulary that marks a tool's trigger domain. Two tools claiming the same
# domain is not automatically wrong — but nobody had ever looked.
DOMAIN_TERMS = [
    "web", "internet", "browse", "search", "external information", "current information",
    "file", "read", "skill", "plan", "research", "compact", "commit",
]


def bridges(root):
    base = os.path.join(root, "pi-extensions")
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        idx = os.path.join(base, name, "index.ts")
        if os.path.isfile(idx):
            out.append((name, idx))
    return out


def strip_comments(src):
    """Comments explaining a past bug often quote the bad phrasing verbatim.
    Auditing them would flag the explanation instead of the instruction."""
    src = re.sub(r"/\*[\s\S]*?\*/", "", src)
    return "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("//"))


def extract_strings(block):
    """Double-quoted string literals, unescaped."""
    return [s.replace('\\"', '"').replace("\\n", "\n")
            for s in re.findall(r'"((?:[^"\\]|\\.)*)"', block)]


def collect(src):
    """Return (guidance_lines, tool_names) for one bridge."""
    body = strip_comments(src)
    guidance = []

    for m in re.finditer(r"promptGuidelines\s*:\s*\[", body):
        depth, i = 0, m.end() - 1
        while i < len(body):
            if body[i] == "[":
                depth += 1
            elif body[i] == "]":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        guidance.extend(extract_strings(body[m.end():i]))

    for m in re.finditer(r"promptSnippet\s*:\s*", body):
        tail = body[m.end():m.end() + 800]
        strings = extract_strings(tail.split("\n\n")[0])
        if strings:
            guidance.append(strings[0])

    for m in re.finditer(r"description\s*:\s*", body):
        tail = body[m.end():m.end() + 2000]
        chunk = tail[:tail.find("\n    ")] if "\n    " in tail else tail[:600]
        strings = extract_strings(chunk)
        if strings:
            joined = " ".join(strings)
            if len(joined) > 40:
                guidance.append(joined)

    names = re.findall(r'name\s*:\s*"([a-z_][a-z_0-9]*)"', body)
    return guidance, names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--show", action="store_true", help="print every injected line")
    args = ap.parse_args()

    root = args.root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print("Repo root: %s" % root)

    failures = 0
    warnings = 0
    domain_owners = {}
    total_chars = 0

    for name, path in bridges(root):
        with open(path, encoding="utf-8") as f:
            src = f.read()
        guidance, tools = collect(src)
        chars = sum(len(g) for g in guidance)
        total_chars += chars
        if guidance:
            print("\n%-26s %2d injected line(s), %5d chars  tools: %s"
                  % (name, len(guidance), chars, ", ".join(sorted(set(tools))) or "-"))
        if args.show:
            for g in guidance:
                print("    | %s" % g[:160])

        for g in guidance:
            low = g.lower()
            for pattern, why in ABSOLUTE_PATTERNS:
                if re.search(pattern, low):
                    print("  FAIL: %s %s\n        %s" % (name, why, g[:160]))
                    failures += 1
            for term in DOMAIN_TERMS:
                if term in low:
                    domain_owners.setdefault(term, set()).add(name)

    print("\nTotal injected guidance: %d chars (~%d tokens) across every turn" % (total_chars, total_chars // 4))

    # Coverage gap, stated rather than hidden: bridges that append to
    # event.systemPrompt inject free-form text this checker does not parse. A
    # silent blind spot in a conflict checker is worse than a named one.
    raw = []
    for name, path in bridges(root):
        with open(path, encoding="utf-8") as f:
            if "systemPrompt:" in strip_comments(f.read()):
                raw.append(name)
    if raw:
        print("\nNOT COVERED — these bridges append free-form text to event.systemPrompt,")
        print("which this checker does not parse. Read them together when changing wording:")
        for name in raw:
            print("  %s" % name)

    shared = {t: sorted(b) for t, b in domain_owners.items() if len(b) > 1}
    if shared:
        print("\nShared trigger vocabulary (not necessarily wrong — but nobody had looked):")
        for term, owners in sorted(shared.items()):
            print("  %-24s claimed by: %s" % (term, ", ".join(owners)))
            warnings += 1

    print("\nPrompt conflict check complete: %d failure(s), %d shared-vocabulary warning(s)."
          % (failures, warnings))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
