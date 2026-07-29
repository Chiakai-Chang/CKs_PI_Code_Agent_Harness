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


class TestCatalogStaysSmall(unittest.TestCase):
    """Reading the catalogue is a tool result the model swallows whole.

    With descriptions it was 42,229 chars (~10,557 tokens). In a live trigger
    test the model read it, its prompt went 16,613 -> 27,715 tokens, and its
    very next turn answered a question that had never been asked — it lost the
    conversation entirely. A mechanism that saves ~11,500 tokens per turn must
    not inject ~10,700 the moment it is used.
    """

    def setUp(self):
        self.path = os.path.join(ROOT, "pi-config", "skill-catalog.json")
        if not os.path.exists(self.path):
            self.skipTest("run scripts/restore.py first")
        with open(self.path, encoding="utf-8") as f:
            self.catalog = json.load(f)

    def test_entries_carry_no_descriptions(self):
        for s in self.catalog["skills"]:
            self.assertNotIn(
                "description", s,
                "catalog entries must be name+path only; the SKILL.md the model "
                "reads next already opens with the description",
            )

    def test_catalog_is_small_enough_to_read_whole(self):
        size = os.path.getsize(self.path)
        self.assertLess(
            size, 20000,
            "skill-catalog.json is %d bytes; reading it would dump ~%d tokens into "
            "the conversation in one tool result" % (size, size // 4),
        )

    def test_one_line_per_entry(self):
        """Pretty-printed, 104 skills came to 525 lines and the model read it
        with limit:300 — half the catalogue was outside the read it performed."""
        with open(self.path, encoding="utf-8") as f:
            lines = len(f.readlines())
        self.assertLess(lines, len(self.catalog["skills"]) + 10)


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


class TestLocalSkillTiering(unittest.TestCase):
    """pi-skills/core and pi-skills/optional were copied into the agent dir
    wholesale, so the tiering that external/* skills go through never applied to
    them.

    Measured on the real system prompt (PI_HARNESS_DUMP_PROMPT, 2026-07-29):
    60 natively registered skills = 6,446 tokens of <available_skills>, 46% of a
    14,057-token system prompt — against 642 tokens for the 104 catalogued ones.
    The catalogued ones cost ~6 tokens each; the natively registered ones ~307.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_non_core_local_skills_go_to_the_catalog(self):
        write_skill(self.tmp, "brainstorming", name="brainstorming")
        write_skill(self.tmp, "nothing-design", name="nothing-design")
        write_skill(self.tmp, "cua-commander", name="cua-commander")
        kept, tail = restore.tier_local_skills(self.tmp, {"brainstorming"})
        self.assertEqual(kept, {"brainstorming"})
        self.assertEqual(sorted(e["name"] for e in tail), ["cua-commander", "nothing-design"])
        for e in tail:
            self.assertTrue(e["path"].endswith("SKILL.md"))

    def test_directory_without_a_skill_md_is_not_catalogued(self):
        """pi-skills/core/bridges holds decision docs, not a skill."""
        os.makedirs(os.path.join(self.tmp, "bridges"), exist_ok=True)
        kept, tail = restore.tier_local_skills(self.tmp, set())
        self.assertEqual(tail, [])

    def test_missing_root_is_not_fatal(self):
        kept, tail = restore.tier_local_skills(os.path.join(self.tmp, "nope"), {"x"})
        self.assertEqual((kept, tail), (set(), []))

    def test_catalog_merge_is_deduplicated_and_sorted(self):
        path = os.path.join(self.tmp, "catalog.json")
        restore.write_catalog(path, [{"name": "zeta", "path": "z/SKILL.md"}])
        restore.merge_into_catalog(path, [
            {"name": "alpha", "path": "a/SKILL.md"},
            {"name": "zeta", "path": "OTHER/SKILL.md"},
        ])
        data = json.load(open(path, encoding="utf-8"))
        names = [s["name"] for s in data["skills"]]
        self.assertEqual(names, ["alpha", "zeta"])
        self.assertEqual([s for s in data["skills"] if s["name"] == "zeta"][0]["path"],
                         "z/SKILL.md", "an existing entry must win over a duplicate")


if __name__ == "__main__":
    unittest.main()
