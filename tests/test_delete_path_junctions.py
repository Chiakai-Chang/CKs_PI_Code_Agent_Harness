"""delete_path says it handles junctions. It cannot.

`~/.pi/agent/skills/` on this machine holds Windows junctions into
`~/.agents/skills/` — `st_reparse_tag 0xa0000003` is IO_REPARSE_TAG_MOUNT_POINT.
Python reports them `islink() == False, isdir() == True`, so delete_path takes
its rmtree branch:

    shutil.rmtree(path, onexc=remove_readonly)

CPython refuses to rmtree a link, and with `onexc` supplied it routes that
refusal to the handler and returns rather than raising. The handler here swallows
everything, so the `except OSError:` fallback underneath — the one whose comment
reads "Fallback for junctions" — never runs. Measured directly:

    >>> shutil.rmtree(brandkit)
    OSError: Cannot call rmtree on a symbolic link

A restore run then reported pruning 15 such directories while 14 survived
untouched, because nothing in delete_path could raise.

This matters past cosmetics: `managed_skills` entries are removed with this same
function, so a managed skill that happens to be a junction is never replaced.
`clear_dir` carries the identical construction.

The property that must never break is at the bottom: removing a junction must not
touch what it points at.
"""

import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

spec = importlib.util.spec_from_file_location("restore", os.path.join(ROOT, "scripts", "restore.py"))
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)

IS_WINDOWS = os.name == "nt"


def make_junction(link, target):
    """mklink /J needs no elevation, unlike a directory symlink."""
    r = subprocess.run(["cmd", "/c", "mklink", "/J", link, target],
                       capture_output=True, text=True)
    return r.returncode == 0


@unittest.skipUnless(IS_WINDOWS, "junctions are a Windows construct")
class TestDeletePathOnJunctions(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="junction-")
        self.addCleanup(lambda: shutil.rmtree(self.base, ignore_errors=True))
        self.target = os.path.join(self.base, "target")
        os.makedirs(self.target)
        with open(os.path.join(self.target, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: real\n---\n")
        self.link = os.path.join(self.base, "link")
        if not make_junction(self.link, self.target):
            self.skipTest("could not create a junction on this filesystem")

    def test_a_junction_is_actually_removed(self):
        restore.delete_path(self.link)
        self.assertFalse(os.path.lexists(self.link))

    def test_removing_a_junction_leaves_the_target_intact(self):
        """The junctions found live pointed into ~/.agents/skills/, which this
        harness does not own. Following one while deleting would destroy another
        tool's content."""
        restore.delete_path(self.link)
        self.assertTrue(os.path.exists(os.path.join(self.target, "SKILL.md")))

    def test_a_junction_whose_target_is_gone_is_still_removed(self):
        broken_target = os.path.join(self.base, "gone")
        os.makedirs(broken_target)
        broken = os.path.join(self.base, "broken")
        if not make_junction(broken, broken_target):
            self.skipTest("could not create a junction")
        os.rmdir(broken_target)
        restore.delete_path(broken)
        self.assertFalse(os.path.lexists(broken))


@unittest.skipUnless(IS_WINDOWS, "junctions are a Windows construct")
class TestClearDirOnJunctions(unittest.TestCase):
    """clear_dir carried the same swallow-everything rmtree construction."""

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="cleardir-")
        self.addCleanup(lambda: shutil.rmtree(self.base, ignore_errors=True))
        self.target = os.path.join(self.base, "target")
        os.makedirs(self.target)
        with open(os.path.join(self.target, "keep.md"), "w", encoding="utf-8") as f:
            f.write("do not follow the junction")
        self.holder = os.path.join(self.base, "holder")
        os.makedirs(self.holder)
        if not make_junction(os.path.join(self.holder, "link"), self.target):
            self.skipTest("could not create a junction on this filesystem")
        with open(os.path.join(self.holder, "plain.txt"), "w") as f:
            f.write("x")
        os.makedirs(os.path.join(self.holder, "subdir"))

    def test_clears_junctions_alongside_ordinary_entries(self):
        restore.clear_dir(self.holder)
        self.assertEqual(sorted(os.listdir(self.holder)), [])

    def test_does_not_reach_through_a_junction_it_clears(self):
        restore.clear_dir(self.holder)
        self.assertTrue(os.path.exists(os.path.join(self.target, "keep.md")))

    def test_clearing_a_path_that_is_itself_a_junction_spares_the_target(self):
        """The worst shape of this bug. `clear_dir` checks `islink` before
        deciding whether to walk, and `islink` is False for a junction, so it
        would os.listdir straight through the link and delete the contents of
        whatever it pointed at."""
        link = os.path.join(self.base, "as-dir")
        if not make_junction(link, self.target):
            self.skipTest("could not create a junction")
        restore.clear_dir(link)
        self.assertTrue(os.path.exists(os.path.join(self.target, "keep.md")))


class TestDeletePathStillHandlesOrdinaryPaths(unittest.TestCase):
    """The junction fix must not cost the cases that already worked."""

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="deletepath-")
        self.addCleanup(lambda: shutil.rmtree(self.base, ignore_errors=True))

    def test_removes_a_populated_directory_tree(self):
        d = os.path.join(self.base, "tree", "nested")
        os.makedirs(d)
        with open(os.path.join(d, "f.txt"), "w") as f:
            f.write("x")
        restore.delete_path(os.path.join(self.base, "tree"))
        self.assertFalse(os.path.exists(os.path.join(self.base, "tree")))

    def test_removes_a_single_file(self):
        p = os.path.join(self.base, "f.txt")
        with open(p, "w") as f:
            f.write("x")
        restore.delete_path(p)
        self.assertFalse(os.path.exists(p))

    def test_a_path_that_does_not_exist_is_not_an_error(self):
        restore.delete_path(os.path.join(self.base, "nope"))


if __name__ == "__main__":
    unittest.main()
