"""The repo is not what runs, and nothing was checking the difference.

Measured 2026-08-08. `Task_003_cwd_confusion` shipped `harness-root.ts` and wired
it into the containment refusal: 910 tests green, verify-bridges 0 failures,
committed and pushed. Then a sweep of `~/.pi/agent/extensions/yes-hooks-bridge/`
found no `harness-root.ts` at all, and an `index.ts` with no `harnessRootHint` —
`setup.py --mode restore` was never run after the edit, so Pi spent the day
loading the version from before the fix. A full day's work was inert and every
check said pass.

That the copies are what Pi loads is not an assumption: `restore.py:1100-1109`
records that Pi auto-discovers `~/.pi/agent/extensions/*/index.ts` by directory,
and that also listing the repo paths in settings.json made each bridge load from
BOTH places until `registerTool()` collided and Pi failed to start.

CLAUDE.md has said "Pi runs installed copies, not your repo files" since the
first time this happened. Discipline is what we had, and discipline is what
failed. This is the mechanism.

Three shapes, because the defect had a shape the obvious check would miss:

* **missing** — what actually happened. A hash comparison over files present in
  both trees reports nothing at all for a file that never arrived.
* **changed** — the ordinary case, an edit without a restore.
* **extra** — a module renamed in the repo leaves the old one installed. Restore
  deletes the bridge directory first so this cannot survive a restore; seeing it
  means no restore has run since the rename.

`package.json` is exempt from exactly one field. `restore.py:1279` injects
`pi-harness.root` with this machine's absolute path, so those thirteen files
differ by design. Exempting the whole file would be the cheaper thing to write
and would hide every other package.json defect behind the exemption — a
threshold defines the shape of the evasion. Only the injected field is
normalised.
"""

import importlib.util
import json
import os
import shutil
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

spec = importlib.util.spec_from_file_location(
    "verify_bridges", os.path.join(ROOT, "scripts", "verify-bridges.py"))
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def write(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


class Trees(unittest.TestCase):
    """A two-bridge repo tree and its installed copy, identical to start."""

    BRIDGES = ["alpha-bridge", "beta-bridge"]

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="drift-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = os.path.join(self.tmp, "pi-extensions")
        self.installed = os.path.join(self.tmp, "installed")
        for b in self.BRIDGES:
            write(os.path.join(self.repo, b, "index.ts"), "export const x = 1;\n")
            write(os.path.join(self.repo, b, "helper.ts"), "export const y = 2;\n")
            # Copied from a real one: all thirteen repo package.json files carry
            # this placeholder, checked 2026-08-08. The first draft of this
            # fixture invented a file without the field, which made every bridge
            # read as drift and sent me looking for a bug in the comparison.
            write(os.path.join(self.repo, b, "package.json"),
                  json.dumps({"name": b, "version": "1.0.0",
                              "pi-harness": {"root": "TODO_SET_BY_RESTORE"}}, indent=2))
        shutil.copytree(self.repo, self.installed, dirs_exist_ok=True)
        # What restore does to every installed package.json, and only there.
        for b in self.BRIDGES:
            p = os.path.join(self.installed, b, "package.json")
            with open(p, encoding="utf-8") as f:
                pkg = json.load(f)
            pkg["pi-harness"] = {"root": "D:/wherever/this/machine/put/it"}
            write(p, json.dumps(pkg, indent=2))

    def drift(self):
        return verify.installed_drift(self.repo, self.installed, self.BRIDGES)


class TestItSeesTheThreeShapes(Trees):
    def test_a_faithful_install_has_no_drift(self):
        """Including the injected root, which is present on every real machine
        and must not read as drift or the check is noise from the first run."""
        self.assertEqual(self.drift(), [])

    def test_a_file_that_never_arrived(self):
        """The 2026-08-08 defect. Comparing only files present in both trees
        returns clean here, which is why this case is first."""
        os.remove(os.path.join(self.installed, "alpha-bridge", "helper.ts"))
        self.assertIn(("missing", "alpha-bridge/helper.ts"), self.drift())

    def test_an_edit_without_a_restore(self):
        write(os.path.join(self.repo, "beta-bridge", "index.ts"),
              "export const x = 99;\n")
        self.assertIn(("changed", "beta-bridge/index.ts"), self.drift())

    def test_a_module_renamed_in_the_repo_leaves_the_old_one_installed(self):
        os.rename(os.path.join(self.repo, "alpha-bridge", "helper.ts"),
                  os.path.join(self.repo, "alpha-bridge", "renamed.ts"))
        found = self.drift()
        self.assertIn(("missing", "alpha-bridge/renamed.ts"), found)
        self.assertIn(("extra", "alpha-bridge/helper.ts"), found)

    def test_a_nested_file_is_compared_too(self):
        """Bridges have subdirectories; a check that only reads the top level
        would pass while the module doing the work sat stale underneath."""
        write(os.path.join(self.repo, "alpha-bridge", "sub", "deep.ts"), "1\n")
        self.assertIn(("missing", "alpha-bridge/sub/deep.ts"), self.drift())


class TestThePackageJsonExemptionIsOneField(Trees):
    def test_the_injected_root_alone_is_not_drift(self):
        p = os.path.join(self.installed, "alpha-bridge", "package.json")
        with open(p, encoding="utf-8") as f:
            pkg = json.load(f)
        pkg["pi-harness"]["root"] = "/somewhere/else/entirely"
        write(p, json.dumps(pkg, indent=2))
        self.assertEqual(self.drift(), [])

    def test_any_other_package_json_difference_is_drift(self):
        """The reason the exemption is a field and not a filename."""
        p = os.path.join(self.installed, "alpha-bridge", "package.json")
        with open(p, encoding="utf-8") as f:
            pkg = json.load(f)
        pkg["version"] = "0.0.1-stale"
        write(p, json.dumps(pkg, indent=2))
        self.assertIn(("changed", "alpha-bridge/package.json"), self.drift())

    def test_an_unparseable_installed_package_json_is_drift_not_a_crash(self):
        write(os.path.join(self.installed, "beta-bridge", "package.json"), "{ not json")
        self.assertIn(("changed", "beta-bridge/package.json"), self.drift())

    def test_a_repo_file_with_no_injected_section_at_all(self):
        """`restore.py:1278` creates `pi-harness` when the repo file lacks it,
        so the installed copy grows a section the source never had. All thirteen
        current bridges carry the placeholder, but nothing makes a new bridge
        carry it, and that bridge must not read as permanently drifted."""
        write(os.path.join(self.repo, "beta-bridge", "package.json"),
              json.dumps({"name": "beta-bridge", "version": "1.0.0"}, indent=2))
        self.assertEqual(self.drift(), [])


class TestItStaysInsideWhatTheHarnessManages(Trees):
    def test_an_unmanaged_extension_is_not_our_business(self):
        """`~/.pi/agent/extensions/` also holds extensions this repo never
        installed. Reporting those as drift would train the reader to ignore
        the output, which is the same as not having the check."""
        write(os.path.join(self.installed, "someone-elses-ext", "index.ts"), "x\n")
        self.assertEqual(self.drift(), [])

    def test_a_bridge_absent_from_the_install_reports_its_files(self):
        shutil.rmtree(os.path.join(self.installed, "beta-bridge"))
        found = self.drift()
        self.assertIn(("missing", "beta-bridge/index.ts"), found)
        self.assertIn(("missing", "beta-bridge/package.json"), found)


class TestNoInstallIsNotACleanBillOfHealth(Trees):
    """CI checks out a fresh repo with no `~/.pi` at all. Returning an empty
    list there would make the check silently pass everywhere it runs
    automatically, which is how a skip path stops earning its keep."""

    def test_it_is_distinguishable_from_no_drift(self):
        self.assertIsNone(
            verify.installed_drift(self.repo, os.path.join(self.tmp, "nope"),
                                   self.BRIDGES))
        self.assertEqual(self.drift(), [])


class TestTheScriptActuallyRunsIt(unittest.TestCase):
    def _verify_bridges_body(self):
        with open(os.path.join(ROOT, "scripts", "verify-bridges.py"),
                  encoding="utf-8") as f:
            return f.read().split("def verify_bridges", 1)[1]

    def test_verify_bridges_calls_the_drift_check(self):
        self.assertIn("installed_drift(", self._verify_bridges_body(),
                      "a drift function nobody calls is a function, not a check")

    def test_drift_is_a_failure_and_not_a_warning(self):
        """It cost a day. A line in a passing run's output is what the two INFO
        lines already in this script are, and nobody reads those. Anchored past
        the call site inside verify_bridges, because splitting on the first
        occurrence in the file lands on the `def` and measures the docstring."""
        after_call = self._verify_bridges_body().split("installed_drift(", 1)[1]
        self.assertRegex(after_call[:1200], r"errors \+= ")


if __name__ == "__main__":
    unittest.main()
