"""A flag that should apply to one project applied to every project.

Measured 2026-08-08. Re-measuring the advancer meant setting
`enableCaseAdvancer` true in `pi-config/harness-config.json` and running
restore — and that file is global, so for the three minutes of the measurement
any other C.A.S.E. project the user opened would have been driven by the
advancer too. Task_002's output.md listed exactly this limitation
("無法讓旗標只對 fixture 生效") and it has been open since.

`research/prime-agent` keeps continual-harness state local by default and only
promotes durable cross-session lessons to global (refinement.ts:974). The
direction is adopted; the location is not — theirs is per session, and a
measurement runs in a different directory with a different session, so per
project is what this needs.

Two things make this dangerous to get wrong, and both are tested first:

* `enableCaseAdvancer` is the flag that TRIGGERS TURNS. Reading it wrong in the
  open direction is worse than any refusal misfiring, so "no local file behaves
  exactly as before" comes before anything else here.
* the local file comes from the project being worked on, which is not
  necessarily the user's own code. A local file that could switch on
  `enableDeepResearch`, or switch off a guard, turns config into an attack
  surface — so the resolver reads one named flag and ignores the rest.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "tests"))
from _scratch import scratch  # per-process temp names; see tests/_scratch.py

MOD = os.path.join(ROOT, "pi-extensions", "case-bridge", "harness-scope.ts")


def _node_major():
    if not shutil.which("node"):
        return 0
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return 0
    m = re.match(r"v(\d+)", out.strip())
    return int(m.group(1)) if m else 0


NODE_OK = _node_major() >= 22


def run_js(script):
    driver = scratch(".tmp_scope_driver.mjs")
    url = "file:///" + MOD.replace("\\", "/")
    with open(driver, "w", encoding="utf-8") as f:
        # `fs` is imported for the snapshot tests, which edit the config file
        # mid-script to prove a running session does not notice.
        f.write("import * as m from %s;\nimport fs from 'node:fs';\n%s"
                % (json.dumps(url), script))
    try:
        p = subprocess.run(["node", driver], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
        if p.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        if os.path.exists(driver):
            os.remove(driver)


class Fixture:
    """A harness root and a project directory, kept apart on purpose."""

    def __init__(self, global_flags=None, local_text=None):
        self.root = tempfile.mkdtemp(prefix="scope-")
        self.harness = os.path.join(self.root, "harness")
        self.project = os.path.join(self.root, "project")
        os.makedirs(os.path.join(self.harness, "pi-config"))
        os.makedirs(self.project)
        if global_flags is not None:
            with open(os.path.join(self.harness, "pi-config", "harness-config.json"),
                      "w", encoding="utf-8") as f:
                json.dump(global_flags, f)
        if local_text is not None:
            with open(os.path.join(self.project, ".pi-harness.json"),
                      "w", encoding="utf-8") as f:
                f.write(local_text)

    def resolve(self, name="enableCaseAdvancer", cwd=None):
        return run_js("""
        // `?? null` because JSON.stringify DROPS a key whose value is
        // undefined, so the absent case arrived as a missing key rather than a
        // value — a hole in the driver reading as a hole in the module.
        process.stdout.write(JSON.stringify({ v: m.resolveFlag(%s, %s, %s) ?? null }));
        """ % (json.dumps(name),
               json.dumps(self.project if cwd is None else cwd),
               json.dumps(self.harness.replace("\\", "/"))))["v"]

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestNoLocalFileChangesNothing(unittest.TestCase):
    """First, and deliberately.

    `enableCaseAdvancer` triggers turns. Every machine today has no local file,
    so if this path drifts even slightly the flag could read true where it reads
    false now, and the harness would start driving sessions nobody asked it to.
    """

    def test_global_true_stays_true(self):
        fx = Fixture(global_flags={"enableCaseAdvancer": True})
        self.addCleanup(fx.cleanup)
        self.assertIs(fx.resolve(), True)

    def test_global_false_stays_false(self):
        fx = Fixture(global_flags={"enableCaseAdvancer": False})
        self.addCleanup(fx.cleanup)
        self.assertIs(fx.resolve(), False)

    def test_a_flag_absent_from_global_is_undefined_not_true(self):
        """The caller owns the default. Returning anything truthy here would
        turn "not configured" into "switched on"."""
        fx = Fixture(global_flags={"somethingElse": True})
        self.addCleanup(fx.cleanup)
        self.assertIsNone(fx.resolve())

    def test_no_global_file_at_all(self):
        fx = Fixture()
        self.addCleanup(fx.cleanup)
        self.assertIsNone(fx.resolve())


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestLocalWinsForThatProjectOnly(unittest.TestCase):
    def test_local_overrides_global(self):
        fx = Fixture(global_flags={"enableCaseAdvancer": False},
                     local_text=json.dumps({"enableCaseAdvancer": True}))
        self.addCleanup(fx.cleanup)
        self.assertIs(fx.resolve(), True)

    def test_another_directory_is_untouched(self):
        """The whole point. A measurement in one project must not drive the
        user's other projects — which is what happened on 2026-08-08."""
        fx = Fixture(global_flags={"enableCaseAdvancer": False},
                     local_text=json.dumps({"enableCaseAdvancer": True}))
        self.addCleanup(fx.cleanup)
        elsewhere = os.path.join(fx.root, "someone-elses-project")
        os.makedirs(elsewhere)
        self.assertIs(fx.resolve(cwd=elsewhere), False)

    def test_a_local_file_without_the_key_falls_through(self):
        fx = Fixture(global_flags={"enableCaseAdvancer": True},
                     local_text=json.dumps({"unrelated": 1}))
        self.addCleanup(fx.cleanup)
        self.assertIs(fx.resolve(), True)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheLocalFileIsATrustBoundary(unittest.TestCase):
    """It arrives with the project being worked on, which is not necessarily
    code the user wrote. A local file that could switch on deep research, or
    switch a guard off, makes config an attack surface."""

    def test_only_scoped_flags_are_readable_from_a_project(self):
        for name in ("enableDeepResearch", "enableCaseBridge", "enableHookAdvisories",
                     "skillTiers", "usableContextTokens"):
            with self.subTest(name=name):
                fx = Fixture(global_flags={name: False},
                             local_text=json.dumps({name: True}))
                self.addCleanup(fx.cleanup)
                self.assertIs(fx.resolve(name=name), False,
                              "a project must not be able to set %s" % name)

    def test_the_scoped_set_is_small_and_named(self):
        out = run_js("""
        process.stdout.write(JSON.stringify({ names: [...m.PROJECT_SCOPED].sort() }));
        """)
        self.assertEqual(out["names"], ["caseClaimRefusalTurns", "enableCaseAdvancer"],
                         "widen this deliberately, one flag at a time, never as a side effect")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestItFailsOpenToGlobal(unittest.TestCase):
    """Unreadable local state must mean "no local state", never "everything
    off" — a broken file in someone's project should not disable the harness."""

    def test_unparseable_local_file(self):
        fx = Fixture(global_flags={"enableCaseAdvancer": True}, local_text="{ not json")
        self.addCleanup(fx.cleanup)
        self.assertIs(fx.resolve(), True)

    def test_local_file_is_not_an_object(self):
        """Four shapes, because the mutation sweep showed one was not enough:
        both `&&` in the object test survived against the array case alone.

        `null` is the sharp one. It parses as JSON, `typeof null` is "object",
        and `key in null` throws — so a project shipping a file containing the
        four characters `null` could take the resolver down."""
        for text in ("[1,2,3]", "null", '"a string"', "42"):
            with self.subTest(text=text):
                fx = Fixture(global_flags={"enableCaseAdvancer": True}, local_text=text)
                self.addCleanup(fx.cleanup)
                self.assertIs(fx.resolve(), True)

    def test_no_cwd_known(self):
        fx = Fixture(global_flags={"enableCaseAdvancer": True},
                     local_text=json.dumps({"enableCaseAdvancer": False}))
        self.addCleanup(fx.cleanup)
        for cwd in ("", None):
            with self.subTest(cwd=cwd):
                self.assertIs(fx.resolve(cwd=cwd or ""), True)

    def test_no_harness_root_and_no_local(self):
        out = run_js("""
        process.stdout.write(JSON.stringify({ v: m.resolveFlag("enableCaseAdvancer", "", "") ?? null }));
        """)
        self.assertIsNone(out["v"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheBridgeUsesIt(unittest.TestCase):
    def test_case_advancer_reads_the_session_snapshot(self):
        """Changed 2026-08-09 with the contract. It used to demand a direct
        `resolveFlag` call, which was right when every read hit the file; the
        flag is now answered from the snapshot taken at session_start, so a
        mid-run edit cannot move a running session."""
        with open(os.path.join(ROOT, "pi-extensions", "case-bridge", "index.ts"),
                  encoding="utf-8") as f:
            src = f.read()
        body = src.split("function caseAdvancerEnabled", 1)[1][:700]
        self.assertIn('scope.get("enableCaseAdvancer")', body)
        self.assertNotIn("resolveFlag(", body,
                         "reading the file here would reintroduce the drift")

    def test_the_snapshot_is_taken_at_a_session_boundary(self):
        """Once, at session_start — the property the whole change exists for."""
        with open(os.path.join(ROOT, "pi-extensions", "case-bridge", "index.ts"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertEqual(src.count("scope.take("), 1, "one boundary, not several")
        started = src.split('pi.on("session_start"', 1)
        self.assertEqual(len(started), 2)
        self.assertIn("scope.take(", started[1][:600])

    def test_the_other_flags_were_left_alone(self):
        """Scope creep here means changing seven bridges at once, none of which
        has a measured problem."""
        with open(os.path.join(ROOT, "pi-extensions", "case-bridge", "index.ts"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertEqual(src.count('scope.get("'), 1)

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestAProjectMayTightenButNeverLoosen(unittest.TestCase):
    """`caseClaimRefusalTurns` exists so an experiment can raise the CLAIM exit
    ramp inside its own fixture instead of editing a shipped constant. The last
    attempt edited the constant, and remembering to revert it is not a
    mechanism.

    But the file arrives with the project, so the direction has to be
    constrained: a project that could set 1 would make the gate stand aside
    after a single turn, which is switching the guard off through the config
    door. Tighter is allowed, looser is not."""

    def _turns(self, value):
        fx = Fixture(global_flags={"enableCaseAdvancer": False},
                     local_text=json.dumps({"caseClaimRefusalTurns": value}))
        self.addCleanup(fx.cleanup)
        return fx.resolve(name="caseClaimRefusalTurns")

    def test_a_stricter_value_is_honoured(self):
        self.assertEqual(self._turns(10), 10)

    def test_a_looser_value_is_refused(self):
        """Below the shipped default is a weakening, whatever the project says."""
        for v in (0, 1, 3, 7, -5):
            with self.subTest(v=v):
                self.assertIsNone(self._turns(v))

    def test_an_absurd_value_is_refused(self):
        """A gate that never lets go locks a model that cannot work out how to
        claim, which is the failure the exit ramp exists to prevent."""
        for v in (13, 1000, 99999):
            with self.subTest(v=v):
                self.assertIsNone(self._turns(v))

    def test_the_band_edges_themselves(self):
        """From the mutation sweep: `min: 4` could be shifted to 5 and `max: 12`
        to 13 with nothing turning red, because the tests only used values well
        inside and well outside. The edges are the contract."""
        self.assertEqual(self._turns(8), 8, "the shipped default must be settable")
        self.assertEqual(self._turns(12), 12)

    def test_a_fraction_is_refused(self):
        """Also from the sweep. `typeof v !== "number" || !Number.isInteger(v)`
        flipped to `&&` lets 4.5 through, because a float clears the typeof test
        and the integer test is then never reached on its own. A fractional
        number of turns is not a number of turns."""
        for v in (8.5, 9.1, 11.9):
            with self.subTest(v=v):
                self.assertIsNone(self._turns(v))

    def test_a_non_number_is_refused(self):
        for v in ("8", True, None, [8]):
            with self.subTest(v=v):
                self.assertIsNone(self._turns(v))

@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestASnapshotHoldsForTheSession(unittest.TestCase):
    """Taken from the-last-harness, which snapshots its experimental flags at
    session start or an explicit reload, so toggling one does not change a
    running session.

    Ours read the file on every call. A measurement whose configuration is
    edited mid-run therefore changes behaviour with nothing in the record
    showing it, and "which configuration did this run use" is not a question
    the transcript can answer. That lands directly on this week's weakest
    point: three separate measurement rounds were invalidated by the
    environment rather than the harness."""

    def _snap(self, first, then):
        fx = Fixture(global_flags={"enableCaseAdvancer": False},
                     local_text=json.dumps(first))
        self.addCleanup(fx.cleanup)
        return run_js("""
        const s = new m.ScopeSnapshot();
        s.take(%s, %s);
        const before = s.get("enableCaseAdvancer");
        %s
        const after = s.get("enableCaseAdvancer");
        process.stdout.write(JSON.stringify({ before, after,
                                              digest: s.digest().length }));
        """ % (json.dumps(fx.project), json.dumps(fx.harness.replace("\\", "/")),
               ("""
        fs.writeFileSync(%s, %s);
        """ % (json.dumps(os.path.join(fx.project, ".pi-harness.json").replace("\\", "/")),
               json.dumps(json.dumps(then)))) if then is not None else ""))

    def test_a_mid_session_edit_does_not_change_the_running_session(self):
        out = self._snap({"enableCaseAdvancer": True}, {"enableCaseAdvancer": False})
        self.assertIs(out["before"], True)
        self.assertIs(out["after"], True, "the snapshot is the session's answer")

    def test_the_snapshot_reflects_the_file_at_the_moment_it_was_taken(self):
        self.assertIs(self._snap({"enableCaseAdvancer": False}, None)["before"], False)

    def test_it_has_a_digest_so_a_run_can_say_what_it_used(self):
        """Half the value is behavioural and half is legible: without something
        identifying the configuration, a reproducible run is still an
        unattributable one."""
        self.assertGreater(self._snap({"enableCaseAdvancer": True}, None)["digest"], 8)

    def test_the_digest_is_pinned_and_distinguishes_configurations(self):
        """The sweep could shift the hash constants with nothing red, because
        only the digest's LENGTH was asserted. A digest nobody compares is a
        label, not an identifier."""
        out = run_js("""
        const a = new m.ScopeSnapshot(), b = new m.ScopeSnapshot();
        a.take("", "");
        b.take("", "");
        const empty = a.digest();
        const same = b.digest();
        process.stdout.write(JSON.stringify({ empty, same }));
        """)
        self.assertEqual(out["empty"], out["same"], "same configuration, same digest")
        # Pinned to the MEASURED value, not the one I assumed. My first guess
        # was scope:00000000:0 on the reasoning that an empty config hashes to
        # zero; it hashes the string "[]", which does not.
        self.assertEqual(out["empty"], "scope:00000b62:0",
                         "an empty configuration has one spelling, and it is pinned")

    def test_reset_puts_it_back_to_untaken(self):
        """From the mutation sweep: the `taken = false` initialiser could be
        flipped to true with nothing turning red, which would make a snapshot
        that was never read answer with values instead of undefined. The
        existing untaken test could not see it because an unread snapshot is
        also an empty one — `get` returns undefined either way. Taking a real
        snapshot first and then resetting is what separates them."""
        fx = Fixture(global_flags={"enableCaseAdvancer": False},
                     local_text=json.dumps({"enableCaseAdvancer": True}))
        self.addCleanup(fx.cleanup)
        out = run_js("""
        const s = new m.ScopeSnapshot();
        s.take(%s, %s);
        const before = s.get("enableCaseAdvancer");
        s.reset();
        process.stdout.write(JSON.stringify({ before,
                                              after: s.get("enableCaseAdvancer") ?? null }));
        """ % (json.dumps(fx.project), json.dumps(fx.harness.replace("\\", "/"))))
        self.assertIs(out["before"], True)
        self.assertIsNone(out["after"], "a reset snapshot must answer undefined")

    def test_an_untaken_snapshot_answers_undefined_not_a_default(self):
        """Answering `false` before session_start would make a missing snapshot
        indistinguishable from a flag that is off — and this flag triggers
        turns."""
        out = run_js("""
        const s = new m.ScopeSnapshot();
        process.stdout.write(JSON.stringify({ v: s.get("enableCaseAdvancer") ?? null }));
        """)
        self.assertIsNone(out["v"])



if __name__ == "__main__":
    unittest.main()
