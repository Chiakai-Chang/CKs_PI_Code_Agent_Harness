"""A bridge switch must not report ON just because it is not running under Pi.

Every bridge finds `harness-config.json` by first locating its own directory.
The way they all did it was `require.resolve("./package.json")`. Pi's loader
shims `require`, so production was fine — but bare node does not, the call
throws, and every one of those readers is wrapped in a `catch` that returns the
DEFAULT. The default is `true`.

So outside Pi, every switch in this harness reported ON no matter what
`harness-config.json` said.

That is not a theoretical problem. It invalidated the first A/B this repo ever
ran on a guard: on 2026-08-16 `measure-drift.py --flag enableNoPlanGate` was
verified against the INSTALLED bridge and both arms came back BLOCKED. The flag
looked broken. The flag was fine; the config reader could not fail any other way.
A measurement harness that cannot turn a mechanism off measures nothing, and it
would have reported "no effect" — the most expensive wrong answer available.

The repo already knew. `skill-catalog-bridge/index.ts` uses `import.meta.url`
with a comment saying exactly why, and `case-bridge/calibration.ts` and
`task-shape-bridge/calibration.ts` each carry a paragraph about it. Three
written explanations, eight unconverted call sites, and nothing that would fail.
This is the file that fails.

`import.meta.url` is ESM-native and identical in both runtimes.
"""

import os
import re
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRIDGES = ROOT / "pi-extensions"

# The call, not the word: `require` appears in prose all over these files, and a
# check that fires on its own documentation gets switched off.
REQUIRE_SELF_PATH = re.compile(r"require\.resolve\s*\(")


def bridge_sources():
    for p in sorted(BRIDGES.rglob("*.ts")):
        if "node_modules" in p.parts:
            continue
        yield p


def strip_comments(text):
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    text = re.sub(r"//.*$", "", text, flags=re.M)
    return text


class TestNoBridgeLocatesItselfWithRequire(unittest.TestCase):
    def test_the_scan_sees_the_bridges(self):
        """An exclusion-based check that reads nothing passes forever."""
        self.assertGreater(len(list(bridge_sources())), 20)

    def test_no_call_to_require_resolve(self):
        bad = []
        for path in bridge_sources():
            src = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
            for m in REQUIRE_SELF_PATH.finditer(src):
                bad.append("%s:%d" % (path.relative_to(ROOT).as_posix(),
                                      src[:m.start()].count("\n") + 1))
        self.assertEqual(
            bad, [],
            "these locate themselves with require.resolve, which throws under "
            "bare node and leaves the surrounding catch returning the default — "
            "every switch then reads ON whatever the config says: %s" % bad)

    def test_the_replacement_is_actually_used(self):
        """The other direction. If nothing resolves through import.meta.url the
        check above is passing on files that stopped reading their config at
        all."""
        users = [p.name for p in bridge_sources()
                 if "import.meta.url" in p.read_text(encoding="utf-8", errors="replace")]
        self.assertGreater(len(users), 4, "only %s use import.meta.url" % users)


class TestASwitchCanActuallyBeTurnedOff(unittest.TestCase):
    """The property the A/B harness depends on, asserted on the source because
    the runtime half is proven by `measure-drift.py --flag` flipping a real run.

    A reader whose failure mode is the default is only safe when the default is
    the safe answer. For a SWITCH the default is `true`, so a failure means the
    mechanism silently stays on — invisible in production and fatal to any
    measurement.
    """

    FLAG = re.compile(r"\.enable[A-Z]\w*")

    def test_every_flag_read_goes_through_a_config_helper(self):
        """Reading `harness-config.json` in more than one place per bridge is how
        one reader gets fixed and the others do not — which is what happened here
        on 2026-08-16, twice in the same file."""
        offenders = []
        for path in bridge_sources():
            src = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
            reads = len(re.findall(r'harness-config\.json', src))
            if reads > 1:
                offenders.append("%s (%d places read harness-config.json)"
                                 % (path.relative_to(ROOT).as_posix(), reads))
        self.assertEqual(offenders, [], "; ".join(offenders))


if __name__ == "__main__":
    unittest.main()
