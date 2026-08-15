"""`$PI_HARNESS_ROOT` must reach the shell the model actually opens.

Ten instruction files — `pi-skills/commands/case.md` (four uses),
`pi-rules/AGENTS.md`, `hello-reflect/SKILL.md`, `camofox-stealth/SKILL.md` and
its `browse.md` — tell the model to run `$PI_HARNESS_ROOT/...` in bash. Until
2026-08-16 that variable was empty in every shell it opened.

`restore.py` wrote `settings.env.PI_HARNESS_ROOT` into
~/.pi/agent/settings.json and `pi-rules/AGENTS.md` told the reader it was
"injected by scripts/restore.py". Pi's `Settings` interface (installed
`core/settings-manager.d.ts`, lines 66-116) has no `env` field and the runtime
never reads one. A zombie config, and the kind this repo's own guidelines forbid.

What it cost, measured on session 01a004bc (2026-08-15), a `/case` run in an
unrelated project: the command's own text says to run
`$PI_HARNESS_ROOT/external/Local-Agent-Workspace/scripts/bootstrap.py`. The model
echoed the variable, got `[]`, and went hunting for the harness by guessing
absolute paths — 41 of its 224 tool calls (18%) landed inside this repo instead
of the user's project. Across all 53 real sessions in other projects: 218 of
2832 calls, 7%.

The fix is one assignment in skill-namespace-guard, and the reason it works is
mechanical: the bash tool rebuilds its environment per call from `getShellEnv()`,
which spreads `process.env` (installed `utils/shell.js:103`, called by
`resolveSpawnContext` in `core/tools/bash.js:119`). Extensions run in that same
process.

These tests drive the real extension and then read the variable back the way a
spawned shell would, because "it is in the config" is precisely the belief that
was wrong for weeks.
"""

import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GUARD = ROOT / "pi-extensions" / "skill-namespace-guard" / "index.ts"

import sys as _sys
_sys.path.insert(0, os.path.join(str(ROOT), "tests"))
from _scratch import scratch  # noqa: E402


def node_ok():
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30)
        return out.returncode == 0 and int(out.stdout.strip().lstrip("v").split(".")[0]) >= 22
    except Exception:
        return False


NODE_OK = node_ok()


@unittest.skipUnless(NODE_OK, "node >= 22 required for native TypeScript type stripping")
class TestItReachesASpawnedShell(unittest.TestCase):
    DRIVER = r"""
import { spawnSync } from "node:child_process";
import mod from %(mod)s;
const preset = process.argv[2] === "preset";
if (preset) process.env.PI_HARNESS_ROOT = "/operator/said/so";
mod({ on() {}, sendMessage() {}, registerTool() {} });
// Read it back the way the bash tool does: a child process inheriting
// process.env. Asserting on process.env directly would prove less than the
// settings block did.
const r = spawnSync(process.execPath, ["-e", "process.stdout.write(String(process.env.PI_HARNESS_ROOT ?? ''))"],
                    { encoding: "utf-8" });
process.stdout.write(JSON.stringify({ inProcess: process.env.PI_HARNESS_ROOT ?? "", inChild: r.stdout ?? "" }));
"""

    def _run(self, preset=False):
        driver = scratch(".tmp_harness_root_driver.mjs")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(self.DRIVER % {"mod": json.dumps("file:///" + str(GUARD).replace("\\", "/"))})
        try:
            env = dict(os.environ)
            env.pop("PI_HARNESS_ROOT", None)
            p = subprocess.run(["node", driver, "preset" if preset else "plain"],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", cwd=str(ROOT), timeout=120, env=env)
            if p.returncode != 0:
                raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
            return json.loads(p.stdout)
        finally:
            if os.path.exists(driver):
                os.remove(driver)

    def test_a_child_process_sees_it(self):
        """The assertion the settings block could never have passed."""
        got = self._run()
        self.assertTrue(got["inChild"], "a spawned shell still sees nothing")
        self.assertEqual(got["inChild"], got["inProcess"])

    def test_it_points_at_a_real_harness_checkout(self):
        got = self._run()
        root = Path(got["inChild"])
        self.assertTrue((root / "pi-extensions").is_dir(),
                        "%s is not a harness root" % root)
        self.assertTrue((root / "pi-skills").is_dir())

    def test_it_uses_forward_slashes(self):
        """Every consumer is a bash command line. A Windows backslash path there
        is an escape sequence, not a path."""
        self.assertNotIn("\\", self._run()["inChild"])

    def test_an_operator_value_is_not_overwritten(self):
        """Someone who exported it deliberately outranks us."""
        self.assertEqual(self._run(preset=True)["inChild"], "/operator/said/so")


class TestTheZombieConfigIsGone(unittest.TestCase):
    """`settings.env` is not in Pi's Settings interface. Leaving it written makes
    an installed copy look like a working configuration, which is how this
    survived: every audit saw the value and stopped there."""

    def test_restore_no_longer_writes_it(self):
        src = (ROOT / "scripts" / "restore.py").read_text(encoding="utf-8")
        self.assertNotIn('settings["env"]["PI_HARNESS_ROOT"]', src)
        self.assertIn('settings.pop("env", None)', src,
                      "an already-installed settings.json keeps its zombie "
                      "block unless restore prunes it")


class TestTheInstructionsDoNotSendTheModelHunting(unittest.TestCase):
    """The variable being set is half the fix. The other half is that an empty
    one must not read as an invitation to search: the measured session left the
    user's project entirely."""

    def test_the_rules_say_what_to_do_when_it_is_empty(self):
        rules = (ROOT / "pi-rules" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("PI_HARNESS_ROOT", rules)
        self.assertIn("do not leave the project", rules.lower().replace("—", "-"))

    def test_the_rules_no_longer_credit_restore_py(self):
        rules = (ROOT / "pi-rules" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("injected by `scripts/restore.py`", rules)


if __name__ == "__main__":
    unittest.main()
