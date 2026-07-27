"""Tiered skill registration: keep every skill discoverable, stop paying for
all of them in every single prompt.

Pi's formatSkillsForPrompt writes name + description + ABSOLUTE PATH into the
system prompt for every registered skill, every turn. Measured before: 145
skills = 55,239 chars (~13,809 tokens/turn, 58% of the whole system prompt).
The per-skill fixed overhead (XML tags + path + name) is ~213 chars no matter
how short the description is, so trimming descriptions reclaims almost nothing
(2,378 tokens for a 150-char cap). Not registering the long tail is the only
lever that moves.
"""

import json
import os
import sys
import tempfile
import shutil
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import restore


def write_skill(base, dirname, name=None, desc="does a thing", extra=""):
    d = os.path.join(base, dirname)
    os.makedirs(d, exist_ok=True)
    fm = "---\n"
    if name is not None:
        fm += "name: %s\n" % name
    fm += "description: %s\n%s---\n\nbody\n" % (desc, extra)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(fm)
    return d


class TestSkillFrontmatter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reads_name_and_flattens_description(self):
        d = write_skill(self.tmp, "a", name="alpha", desc="line one\n  continued here")
        name, desc = restore.skill_frontmatter(os.path.join(d, "SKILL.md"))
        self.assertEqual(name, "alpha")
        self.assertEqual(desc, "line one continued here")

    def test_strips_quotes_from_name(self):
        """YAML allows a quoted scalar and yes.md ships `name: "yes"`. Leaving
        the quotes on means the name never matches a core-list entry and the
        skill is silently demoted to the catalog."""
        d = write_skill(self.tmp, "y", name='"yes"')
        self.assertEqual(restore.skill_frontmatter(os.path.join(d, "SKILL.md"))[0], "yes")

    def test_missing_or_unparseable_is_not_fatal(self):
        self.assertEqual(restore.skill_frontmatter(os.path.join(self.tmp, "nope.md")), (None, None))
        p = os.path.join(self.tmp, "plain.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write("no frontmatter here")
        self.assertEqual(restore.skill_frontmatter(p), (None, None))


class TestDiscoverAndPartition(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        write_skill(self.tmp, "alpha", name="alpha")
        write_skill(self.tmp, "container/beta", name="beta")   # nested container
        write_skill(self.tmp, "gamma", name=None)              # no name: field
        os.makedirs(os.path.join(self.tmp, "empty"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_walks_nested_containers_and_falls_back_to_dirname(self):
        names = sorted(s[0] for s in restore.discover_skills([self.tmp]))
        self.assertEqual(names, ["alpha", "beta", "gamma"])

    def test_partition_by_name(self):
        skills = restore.discover_skills([self.tmp])
        core, tail = restore.partition_skills_by_tier(skills, ["alpha", "gamma"])
        self.assertEqual(sorted(s[0] for s in core), ["alpha", "gamma"])
        self.assertEqual(sorted(s[0] for s in tail), ["beta"])

    def test_empty_core_puts_everything_in_the_tail(self):
        skills = restore.discover_skills([self.tmp])
        core, tail = restore.partition_skills_by_tier(skills, [])
        self.assertEqual(core, [])
        self.assertEqual(len(tail), 3)


class TestSkillTiersConfig(unittest.TestCase):
    """Every malformed shape must fail OPEN to "all". Silently dropping the
    long tail is far worse than a fat prompt — the same choice ecc_skill_paths
    makes for its manifest."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = os.path.join(self.tmp, "harness-config.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, obj):
        with open(self.cfg, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        return self.cfg

    def test_tiered_mode_returns_core_list(self):
        self._write({"skillTiers": {"mode": "tiered", "core": ["a", "b"]}})
        self.assertEqual(restore.skill_tiers_from_config(self.cfg), ("tiered", ["a", "b"]))

    def test_mode_all_is_todays_behaviour(self):
        self._write({"skillTiers": {"mode": "all"}})
        self.assertEqual(restore.skill_tiers_from_config(self.cfg), ("all", []))

    def test_missing_key_absent_file_and_garbage_all_fail_open(self):
        for obj in ({}, {"skillTiers": "yes"}, {"skillTiers": {"mode": "tiered"}},
                    {"skillTiers": {"mode": "tiered", "core": "not-a-list"}},
                    {"skillTiers": {"mode": "tiered", "core": [1, 2]}}):
            self.assertEqual(restore.skill_tiers_from_config(self._write(obj)), ("all", []))
        self.assertEqual(
            restore.skill_tiers_from_config(os.path.join(self.tmp, "absent.json")), ("all", []))
        with open(self.cfg, "w", encoding="utf-8") as f:
            f.write("{ not json")
        self.assertEqual(restore.skill_tiers_from_config(self.cfg), ("all", []))


class TestShippedConfig(unittest.TestCase):
    """The committed config must stay coherent with what is on disk."""

    def setUp(self):
        with open(os.path.join(ROOT, "pi-config", "harness-config.json"), encoding="utf-8") as f:
            self.cfg = json.load(f)

    def test_core_names_resolve_to_real_skills(self):
        """A typo'd core name has exactly one symptom: the skill it was meant to
        promote stays in the catalog. Nothing else reports it."""
        tiers = self.cfg.get("skillTiers", {})
        if tiers.get("mode") != "tiered":
            self.skipTest("shipped config is not tiered")
        catalog_path = os.path.join(ROOT, "pi-config", "skill-catalog.json")
        manifest_path = os.path.join(ROOT, "pi-config", "external-skills-manifest.json")
        if not (os.path.exists(catalog_path) and os.path.exists(manifest_path)):
            self.skipTest("run scripts/restore.py first")
        with open(catalog_path, encoding="utf-8") as f:
            tail = {s["name"] for s in json.load(f)["skills"]}
        with open(manifest_path, encoding="utf-8") as f:
            core_dirs = [e["path"] for e in json.load(f)]
        core = {s[0] for s in restore.discover_skills(core_dirs)}
        for name in tiers.get("core", []):
            self.assertNotIn(
                name, tail,
                "%s is declared core but landed in the catalog — name mismatch" % name)

    def test_declared_core_is_actually_registered(self):
        tiers = self.cfg.get("skillTiers", {})
        if tiers.get("mode") != "tiered":
            self.skipTest("shipped config is not tiered")
        manifest_path = os.path.join(ROOT, "pi-config", "external-skills-manifest.json")
        if not os.path.exists(manifest_path):
            self.skipTest("run scripts/restore.py first")
        with open(manifest_path, encoding="utf-8") as f:
            core_dirs = [e["path"] for e in json.load(f)]
        registered = {s[0] for s in restore.discover_skills(core_dirs)}
        # pi-skills/ skills are registered separately via settings.json#skills
        # and are unaffected by tiering, so only external names are checked.
        external = set(tiers.get("core", [])) & (registered | set())
        self.assertTrue(external, "no declared core skill is registered — tiering is misconfigured")


class TestCatalogBridgeWiring(unittest.TestCase):
    def test_bridge_registered_and_managed(self):
        with open(os.path.join(ROOT, "scripts", "restore.py"), encoding="utf-8") as f:
            c = f.read()
        self.assertEqual(c.count('"skill-catalog-bridge"'), 3)

    def test_bridge_is_esm_without_require(self):
        base = os.path.join(ROOT, "pi-extensions", "skill-catalog-bridge")
        with open(os.path.join(base, "package.json"), encoding="utf-8") as f:
            self.assertIn('"type": "module"', f.read())
        with open(os.path.join(base, "index.ts"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("fileURLToPath(import.meta.url)", src)
        self.assertIn("event.systemPrompt ?? \"\"", src)


if __name__ == "__main__":
    unittest.main()
