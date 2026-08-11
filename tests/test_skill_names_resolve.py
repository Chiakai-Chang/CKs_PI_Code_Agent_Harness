"""Every skill name this harness tells the model to load must be registered.

Measured 2026-08-11 in the owner's own session, in `D:/MyProject/DiscoverTurth`:

    [skill] research-task-routing
    [skill] planning-with-files
    ENOENT: no such file or directory, access
    '...\\external\\superpowers\\skills\\planning-with-files\\SKILL.md'

The model did exactly what it was told. `research-task-routing` said "Load
`planning-with-files`", `pi-rules/AGENTS.md` §10 said it twice more, and
`CLAUDE.md` said it once — while the skill that is actually registered declares
itself `pi-planning-with-files` in its own frontmatter, because the external
submodule named it that way and `restore.py` shadows the local copy on purpose.

Nothing was broken in the loader. Every routing instruction in the harness named
a skill that cannot be loaded, and the failure landed at the exact moment the
methodology was supposed to start. This test is the guard: the names in the
instructions are checked against the names that get registered, so a rename on
either side turns something red instead of turning the methodology off.
"""

import io
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "pi-config", "external-skills-manifest.json")

# Directories under pi-skills/core/ that restore.py never installs. Kept in step
# with PI_SKILLS_NEVER_INSTALLED there; the test below asserts they agree.
NEVER_INSTALLED = ("bridges", "planning-with-files")


def frontmatter_name(skill_md):
    try:
        raw = io.open(skill_md, encoding="utf-8").read()
    except OSError:
        return None
    m = re.match(r"^---\r?\n([\s\S]*?)\r?\n---", raw)
    if not m:
        return None
    n = re.search(r"^name:\s*(.+?)\s*$", m.group(1), re.M)
    if not n:
        return None
    value = n.group(1).strip()
    q = re.match(r"^([\"'])([\s\S]*)\1$", value)   # `name: "yes"` is quoted YAML
    return q.group(2) if q else value


def registered_names():
    """Every skill name a session can actually load, from the same two sources
    restore.py installs from."""
    names = set()

    for entry in json.load(io.open(MANIFEST, encoding="utf-8")):
        path = entry.get("path") if isinstance(entry, dict) else None
        if not path:
            continue
        # Paths in the manifest are absolute and machine-specific; re-root them
        # so this passes on a fresh checkout as well as on the author's disk.
        rel = path.replace("\\", "/").split("/external/", 1)
        base = os.path.join(ROOT, "external", rel[1]) if len(rel) == 2 else path
        direct = os.path.join(base, "SKILL.md")
        if os.path.isfile(direct):
            n = frontmatter_name(direct)
            names.add(n or os.path.basename(base))
            continue
        # A container directory holding several sub-skills.
        if os.path.isdir(base):
            for sub in sorted(os.listdir(base)):
                sub_md = os.path.join(base, sub, "SKILL.md")
                if os.path.isfile(sub_md):
                    names.add(frontmatter_name(sub_md) or sub)

    core = os.path.join(ROOT, "pi-skills", "core")
    if os.path.isdir(core):
        for name in sorted(os.listdir(core)):
            if name in NEVER_INSTALLED:
                continue
            md = os.path.join(core, name, "SKILL.md")
            if os.path.isfile(md):
                names.add(frontmatter_name(md) or name)
    return names


class TestTheInstructionsNameSkillsThatExist(unittest.TestCase):
    #  file, and the names it tells the model to load
    INSTRUCTIONS = [
        ("pi-skills/core/research-task-routing/SKILL.md",
         ["brainstorming", "pi-planning-with-files"]),
        ("pi-rules/AGENTS.md",
         ["brainstorming", "pi-planning-with-files", "systematic-debugging",
          "test-driven-development", "mece-autopilot", "case-framework"]),
        ("CLAUDE.md",
         ["brainstorming", "pi-planning-with-files", "systematic-debugging",
          "test-driven-development", "mece-autopilot"]),
    ]

    def setUp(self):
        self.registered = registered_names()

    def test_the_registry_is_not_empty(self):
        """A registry that reads as empty would make every assertion below pass
        by accident — the shape of failure this repo keeps meeting."""
        self.assertGreater(len(self.registered), 20,
                           "only found: %s" % sorted(self.registered))

    def test_every_named_skill_is_registered(self):
        for path, names in self.INSTRUCTIONS:
            for name in names:
                with self.subTest(path=path, name=name):
                    self.assertIn(name, self.registered,
                                  "%s tells the model to load `%s`, which no "
                                  "registered skill declares" % (path, name))

    def test_the_instructions_still_mention_each_name(self):
        """The pairing above is only meaningful while the file says it. A doc
        edited to drop the name would leave this test asserting nothing."""
        for path, names in self.INSTRUCTIONS:
            text = io.open(os.path.join(ROOT, path), encoding="utf-8").read()
            for name in names:
                with self.subTest(path=path, name=name):
                    self.assertIn(name, text)

    def test_the_unregistered_spelling_is_gone_from_instructions(self):
        """`planning-with-files` unqualified is the name that failed. It may
        still appear as part of `pi-planning-with-files`, as the bridge name, or
        as a path inside a vendored script — but not as a skill to load."""
        for path, _names in self.INSTRUCTIONS:
            text = io.open(os.path.join(ROOT, path), encoding="utf-8").read()
            for m in re.finditer(r"`([a-z0-9-]*planning-with-files)`", text):
                with self.subTest(path=path, found=m.group(1)):
                    self.assertEqual(m.group(1), "pi-planning-with-files")

    def test_the_never_installed_list_matches_restore(self):
        src = io.open(os.path.join(ROOT, "scripts", "restore.py"),
                      encoding="utf-8").read()
        m = re.search(r"PI_SKILLS_NEVER_INSTALLED\s*=\s*\(([^)]*)\)", src)
        self.assertIsNotNone(m, "restore.py no longer declares the exclusion list")
        found = tuple(re.findall(r'"([^"]+)"', m.group(1)))
        self.assertEqual(found, NEVER_INSTALLED)


if __name__ == "__main__":
    unittest.main()
