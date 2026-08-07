"""Cloned is not reviewed, and reviewed is not remembered.

2026-08-06: a whole day went into rebuilding two mechanisms that
`reference/pi-until-done` already implements — a settled-driven continuation
loop and an evidence judge. Our own notes in
`docs/superpowers/pi-until-done-learnings/02-bounded-execution-and-spin-detection.md`
state, in writing, that `agent_settled` owns automatic continuation and that the
spin guard keys on progress signals rather than turn count. The advancer was
built on `turn_end` with a counter over injections, and a five-run measurement
rediscovered both facts by experiment.

The documents existed. Nothing connected them to the work.

So this is not another document. It is a register with a check: every external
source has to appear in it, every clone on disk has to be a declared source, and
every learnings path it claims has to exist. A source that has never been
reviewed says so in a column, which is the difference between "we have 15
repositories" and "we know what is in them" — nine of the thirteen research
clones were, at the time of writing, mentioned in zero files anywhere in docs/
or pi-skills/, including the four that were supposedly distilled into skills.
"""

import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "check-prior-art.py")
REGISTER = os.path.join(ROOT, "docs", "prior-art", "REGISTER.md")
MANIFEST = os.path.join(ROOT, "external-manifest.json")


def run(args=None, cwd=ROOT):
    p = subprocess.run([sys.executable, SCRIPT] + (args or []),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=cwd, timeout=180)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def manifest_sources():
    with open(MANIFEST, encoding="utf-8") as f:
        data = json.load(f)
    out = []

    def walk(node):
        if isinstance(node, list):
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            if "name" in node and ("path" in node or "url" in node):
                out.append(node)
            else:
                for v in node.values():
                    walk(v)

    walk(data)
    return out


class TestTheRegisterExists(unittest.TestCase):
    def test_the_script_is_there(self):
        self.assertTrue(os.path.exists(SCRIPT))

    def test_the_register_is_there(self):
        self.assertTrue(os.path.exists(REGISTER))


class TestEverySourceIsAccountedFor(unittest.TestCase):
    def test_the_check_passes_on_the_current_tree(self):
        code, out = run()
        self.assertEqual(code, 0, out)

    def test_every_manifest_source_has_a_row(self):
        with open(REGISTER, encoding="utf-8") as f:
            text = f.read()
        missing = [s["name"] for s in manifest_sources() if s["name"] not in text]
        self.assertEqual(missing, [], "sources absent from the register: %s" % missing)

    def test_it_reports_how_many_are_still_unreviewed(self):
        """The number nobody wants to look at is the point of the register."""
        code, out = run()
        self.assertRegex(out, r"(?i)unreviewed|未審視")


class TestReadmeIsTreatedAsAList(unittest.TestCase):
    """The register's first version was built from `external-manifest.json`, and
    that was the wrong starting point: README is the list the owner reads and
    remembers. Cross-checking the three lists immediately produced four drifts,
    the sharpest being that `pi-until-done` — the clone holding the mechanisms
    this project spent a day rebuilding — is linked nowhere in README."""

    def test_every_repository_readme_links_has_a_row(self):
        import re
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        with open(REGISTER, encoding="utf-8") as f:
            register = f.read().lower()
        self_names = {"cks_pi_code_agent_harness", "pi-mono"}
        missing = []
        for _owner, repo in re.findall(
                r"https://github\.(?:com|alchaincyf)/([\w.-]+)/([\w.-]+)", readme):
            name = repo.rstrip("/")
            if name.endswith(".git"):
                name = name[:-4]
            if name.lower() in self_names:
                continue
            if name.lower() not in register:
                missing.append(name)
        self.assertEqual(sorted(set(missing)), [],
                         "linked from README but absent from the register")

    def test_a_readme_repo_missing_from_the_register_fails_the_check(self):
        import shutil
        import tempfile
        d = tempfile.mkdtemp(prefix="prior-art-readme-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        os.makedirs(os.path.join(d, "scripts"))
        os.makedirs(os.path.join(d, "docs", "prior-art"))
        shutil.copyfile(SCRIPT, os.path.join(d, "scripts", "check-prior-art.py"))
        shutil.copyfile(MANIFEST, os.path.join(d, "external-manifest.json"))
        shutil.copyfile(REGISTER, os.path.join(d, "docs", "prior-art", "REGISTER.md"))
        with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
            f.write("see https://github.com/someone/a-repo-nobody-registered\n")
        code, out = run(cwd=d)
        self.assertNotEqual(code, 0, out)
        self.assertIn("a-repo-nobody-registered", out)


class TestItCanActuallyFail(unittest.TestCase):
    """A check that cannot fail is a check that proves nothing. Each of these
    breaks the tree in a temp copy and requires a non-zero exit."""

    def _tree(self):
        import shutil
        import tempfile
        d = tempfile.mkdtemp(prefix="prior-art-")
        os.makedirs(os.path.join(d, "scripts"))
        os.makedirs(os.path.join(d, "docs", "prior-art"))
        shutil.copyfile(SCRIPT, os.path.join(d, "scripts", "check-prior-art.py"))
        shutil.copyfile(MANIFEST, os.path.join(d, "external-manifest.json"))
        shutil.copyfile(REGISTER, os.path.join(d, "docs", "prior-art", "REGISTER.md"))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return d

    def test_a_source_missing_from_the_register_fails(self):
        d = self._tree()
        reg = os.path.join(d, "docs", "prior-art", "REGISTER.md")
        with open(reg, encoding="utf-8") as f:
            text = f.read()
        with open(reg, "w", encoding="utf-8") as f:
            f.write(text.replace("pi-until-done", "pi-until-DELETED"))
        code, out = run(cwd=d)
        self.assertNotEqual(code, 0, out)
        self.assertIn("pi-until-done", out)

    def test_a_clone_on_disk_that_is_not_declared_fails(self):
        d = self._tree()
        os.makedirs(os.path.join(d, "research", "some-undeclared-clone", ".git"))
        code, out = run(cwd=d)
        self.assertNotEqual(code, 0, out)
        self.assertIn("some-undeclared-clone", out)

    def test_a_missing_register_file_fails(self):
        """Counted as a break in the commit message before a test existed for it.
        The claim came first, so the test follows rather than the number being
        quietly dropped."""
        d = self._tree()
        os.remove(os.path.join(d, "docs", "prior-art", "REGISTER.md"))
        code, out = run(cwd=d)
        self.assertNotEqual(code, 0, out)
        self.assertIn("REGISTER.md", out)

    def test_a_learnings_path_that_does_not_exist_fails(self):
        d = self._tree()
        reg = os.path.join(d, "docs", "prior-art", "REGISTER.md")
        with open(reg, "a", encoding="utf-8") as f:
            f.write("\n| fake-source | reference-clone | reference/fake | 已審視 | "
                    "docs/prior-art/no-such-file.md | — | — | 2026-08-06 |\n")
        code, out = run(cwd=d)
        self.assertNotEqual(code, 0, out)
        self.assertIn("no-such-file", out)


if __name__ == "__main__":
    unittest.main()
