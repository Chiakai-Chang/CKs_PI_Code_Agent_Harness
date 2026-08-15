"""TypeScript that Node's native stripping cannot load, caught before Pi does.

Pi and this suite both run bridge modules through Node's `--experimental-strip-types`
path, which ERASES type annotations and does not TRANSFORM anything. A construct
that needs emitted code fails at load with `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`,
and a bridge that will not load is a bridge that silently does nothing.

This check exists because the knowledge already did — and did not help.
`pi-extensions/task-shape-bridge/goal-restate.ts:130` carries a comment saying
`node's strip-only transform ... rejects constructor(private x)`, written by
whoever hit it the first time. On 2026-08-15 the same trap was hit again while
writing `reflect-budget.ts`, because a comment inside one module is not reachable
from the moment somebody writes another.

That is this repo's most repeated shape: not "we did not know", but "we knew and
there was no execution point". The model-swap checklist §1 was right and unread
until it became `scripts/check-model-serving.py`; the mutation allowlist's own
header says its line-number keys expire and they have expired twice. A comment
becomes a check, or it becomes archaeology.

Scope is deliberately narrow: only constructs that are known to FAIL TO LOAD.
This is not a style linter, and adding stylistic rules here would make it
something people turn off.
"""

import os
import re
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRIDGES = ROOT / "pi-extensions"

# Each entry is (name, pattern, why it cannot load).
UNSUPPORTED = [
    (
        "constructor parameter property",
        # `constructor(private x: T)` / `(public readonly y = 1)` — the modifier
        # is what makes it a declaration+assignment, which stripping cannot emit.
        re.compile(r"constructor\s*\([^)]*\b(?:private|public|protected|readonly)\s+\w"),
        "a parameter property declares AND assigns a field; stripping erases the "
        "modifier and the assignment never happens, so Node rejects the file "
        "outright. Use a plain field plus an explicit assignment in the body.",
    ),
    (
        "enum",
        re.compile(r"^\s*(?:export\s+)?(?:const\s+)?enum\s+\w+", re.M),
        "a non-declare enum emits a runtime object. Use a `const` object with "
        "`as const`, or a union of string literals.",
    ),
    (
        "namespace / module block",
        re.compile(r"^\s*(?:export\s+)?(?:namespace|module)\s+\w+\s*\{", re.M),
        "a namespace emits a runtime object. Use ordinary module exports.",
    ),
    (
        "parameter decorator or legacy decorator",
        re.compile(r"^\s*@[A-Za-z_]\w*\s*\(", re.M),
        "decorators emit calls. Not supported by type stripping.",
    ),
]


def bridge_sources():
    for p in sorted(BRIDGES.rglob("*.ts")):
        if "node_modules" in p.parts:
            continue
        yield p


def strip_comments_and_strings(text):
    """Crude but sufficient: the patterns above must not match inside a comment
    that DESCRIBES the trap. goal-restate.ts and reflect-budget.ts both contain
    the words `constructor(private x)` in prose explaining why not to write it,
    and flagging those would make this check fire on its own documentation."""
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    text = re.sub(r"//.*$", "", text, flags=re.M)
    text = re.sub(r"`(?:[^`\\]|\\.)*`", "``", text)
    text = re.sub(r"'(?:[^'\\\n]|\\.)*'", "''", text)
    text = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', text)
    return text


class TestNoBridgeUsesSyntaxThatCannotLoad(unittest.TestCase):
    def test_the_scan_sees_the_bridges(self):
        """An exclusion-based check that reads nothing passes forever."""
        found = list(bridge_sources())
        self.assertGreater(len(found), 20,
                           "only %d bridge .ts files found — wrong root?" % len(found))

    def test_no_unsupported_construct(self):
        bad = []
        for path in bridge_sources():
            src = strip_comments_and_strings(
                path.read_text(encoding="utf-8", errors="replace"))
            for name, pat, why in UNSUPPORTED:
                m = pat.search(src)
                if m:
                    line = src[:m.start()].count("\n") + 1
                    bad.append("%s:%d uses a %s — %s"
                               % (path.relative_to(ROOT).as_posix(), line, name, why))
        self.assertEqual(bad, [], "\n".join(bad))


class TestTheRulesCanFail(unittest.TestCase):
    """Each pattern is fed the construct it exists to reject. Without this the
    whole file could pass on a typo in every regex."""

    SAMPLES = {
        "constructor parameter property": "class A {\n  constructor(private readonly x = 3) {}\n}",
        "enum": "export enum Mode { A, B }",
        "namespace / module block": "export namespace Foo {\n  export const x = 1;\n}",
        "parameter decorator or legacy decorator": "@Injectable()\nclass A {}",
    }

    def test_every_rule_matches_its_own_bad_example(self):
        for name, pat, _why in UNSUPPORTED:
            with self.subTest(rule=name):
                sample = self.SAMPLES[name]
                self.assertTrue(pat.search(strip_comments_and_strings(sample)),
                                "the %r rule does not match %r" % (name, sample))

    def test_the_accepted_form_is_not_flagged(self):
        """The replacement this repo actually uses must stay legal, or the check
        would push people back toward the broken form."""
        ok = ("class A {\n"
              "  private readonly x: number;\n"
              "  constructor(x = 3) {\n    this.x = x;\n  }\n}")
        for name, pat, _why in UNSUPPORTED:
            with self.subTest(rule=name):
                self.assertIsNone(pat.search(strip_comments_and_strings(ok)))

    def test_prose_describing_the_trap_is_not_flagged(self):
        """Both modules that hit this carry a comment naming the construct. A
        check that fires on its own documentation gets switched off."""
        prose = ("// NOT constructor(private readonly maxRuns = 3): node's\n"
                 "// strip-only transform rejects it.\n"
                 "class A { constructor(maxRuns = 3) {} }")
        for name, pat, _why in UNSUPPORTED:
            with self.subTest(rule=name):
                self.assertIsNone(pat.search(strip_comments_and_strings(prose)))


if __name__ == "__main__":
    unittest.main()
