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

    def test_no_core_name_is_satisfied_only_by_a_never_installed_directory(self):
        """A core entry whose only match is an excluded directory is dead.

        `planning-with-files` was declared core for months and was never core.
        The external submodule declares itself `pi-planning-with-files`, so the
        core name matched nothing there and the skill landed in the catalog with
        no description. Nothing reported it, because `pi-skills/core/
        planning-with-files/` exists on disk — restore excludes it from the copy
        on purpose, but its presence made the name look resolved.

        The symptom took a dumped system prompt to see: 43 skills carried
        descriptions and 122 carried names only, and planning-with-files —
        the skill the routing note tells the model to load by name — was in
        the 122.
        """
        tiers = self.cfg.get("skillTiers", {})
        if tiers.get("mode") != "tiered":
            self.skipTest("shipped config is not tiered")
        manifest_path = os.path.join(ROOT, "pi-config", "external-skills-manifest.json")
        if not os.path.exists(manifest_path):
            self.skipTest("run scripts/restore.py first")
        with open(manifest_path, encoding="utf-8") as f:
            core_dirs = [e["path"] for e in json.load(f)]
        external = {s[0] for s in restore.discover_skills(core_dirs)}

        dead = [n for n in tiers.get("core", [])
                if n in restore.PI_SKILLS_NEVER_INSTALLED and n not in external]
        self.assertEqual(
            dead, [],
            "declared core but never registered under that name: %s — the "
            "directory is excluded from the copy, so the entry does nothing" % dead)

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


class TestUsableContextCeiling(unittest.TestCase):
    """llama.cpp is launched with -c 262144 and models.json declared the same,
    so Pi computed its compaction trigger as

        contextTokens > contextWindow - reserveTokens = 262144 - 16384 = 245,760

    while the model measurably starts fabricating tool calls at ~23,000
    (docs/KNOWN_ISSUES.md). Compaction could never fire before quality
    collapsed: the captured runaway reached 51,915 tokens still going.

    The engine's context window is not the usable one. Declaring the usable
    ceiling is what makes compaction protective instead of decorative.
    """

    def test_ceiling_lowers_context_window_and_max_tokens(self):
        models = {"providers": {"local": {"models": [
            {"id": "m", "contextWindow": 262144, "maxTokens": 32768}]}}}
        capped = restore.cap_context_window(models, 26000)
        m = models["providers"]["local"]["models"][0]
        self.assertEqual(m["contextWindow"], 26000)
        self.assertLessEqual(m["maxTokens"], 26000 // 4)
        self.assertEqual(capped, ["m"])

    def test_ceiling_never_raises_a_smaller_window(self):
        """A model genuinely limited to 8k must not be told it has 26k."""
        models = {"providers": {"local": {"models": [
            {"id": "small", "contextWindow": 8192, "maxTokens": 2048}]}}}
        self.assertEqual(restore.cap_context_window(models, 26000), [])
        m = models["providers"]["local"]["models"][0]
        self.assertEqual(m["contextWindow"], 8192)
        self.assertEqual(m["maxTokens"], 2048)

    def test_disabled_by_default_is_a_no_op(self):
        """Platform-agnostic default: other people's models may be fine at full
        context, so an unset ceiling must change nothing."""
        models = {"providers": {"local": {"models": [
            {"id": "m", "contextWindow": 262144, "maxTokens": 32768}]}}}
        for ceiling in (0, None):
            self.assertEqual(restore.cap_context_window(models, ceiling), [])
        self.assertEqual(models["providers"]["local"]["models"][0]["contextWindow"], 262144)

    def test_compaction_settings_fire_inside_the_ceiling(self):
        s = restore.compaction_settings_for(26000)
        self.assertTrue(s["enabled"])
        trigger = 26000 - s["reserveTokens"]
        self.assertLess(trigger, 26000, "compaction must trigger below the ceiling")
        self.assertGreater(trigger, s["keepRecentTokens"],
                           "keeping more than the trigger allows would compact forever")

    def test_compaction_settings_disabled_ceiling_returns_nothing(self):
        self.assertIsNone(restore.compaction_settings_for(0))

    def test_keep_recent_leaves_room_for_the_fixed_per_turn_floor(self):
        """The system prompt is present in every turn, so it is a floor under
        the post-compaction context, not part of what compaction can remove.

        Measured on this harness: 15,287 tokens per turn. With a 26,000 ceiling
        the trigger is 19,500, so keeping Pi's derived 3,250 recent tokens would
        land at 15,287 + summary + 3,250 = over the trigger again — compaction
        would fire forever without ever getting under it.
        """
        s = restore.compaction_settings_for(26000, per_turn_floor=15287)
        trigger = 26000 - s["reserveTokens"]
        self.assertLess(15287 + restore.COMPACTION_SUMMARY_ALLOWANCE + s["keepRecentTokens"],
                        trigger,
                        "post-compaction context must land below the trigger")

    def test_floor_too_large_for_the_ceiling_is_reported(self):
        """No keepRecent value can help when the fixed prompt alone nearly fills
        the usable window — that has to be said out loud, not silently clamped."""
        self.assertIsNone(restore.compaction_headroom_warning(26000, 8000),
                          "a floor with room to spare stays silent")
        w = restore.compaction_headroom_warning(26000, 19000)
        self.assertIsNotNone(w)
        self.assertIn("19000", w)


    def test_thrashing_is_reported_even_when_it_technically_fits(self):
        """Landing just under the trigger is not success.

        Measured setup: floor 15,414, ceiling 26,800, trigger 20,100. Compaction
        lands at 19,588 — below the trigger, so no loop, but only 512 tokens of
        conversation before it fires again. That is thrashing, and calling it
        healthy would hide the real problem: the per-turn prompt is too large
        for this model's usable window.
        """
        w = restore.compaction_headroom_warning(26800, 15414)
        self.assertIsNotNone(w)
        self.assertIn("15414", w)

    def test_comfortable_headroom_is_silent(self):
        self.assertIsNone(restore.compaction_headroom_warning(26800, 8000))


    def test_turning_the_ceiling_off_removes_the_override(self):
        """Disabling usableContextTokens must not leave the derived compaction
        settings behind.

        Observed 2026-07-29: after reverting the ceiling to 0, models.json went
        back to 262,144 but settings.json kept reserveTokens 6700 /
        keepRecentTokens 2974 — so compaction would trigger at 255,444 and keep
        only 2,974 tokens, which is worse than Pi's own defaults. A stale value
        nobody chose is exactly the zombie config CLAUDE.md forbids.
        """
        settings = {"compaction": {"enabled": True, "reserveTokens": 6700, "keepRecentTokens": 2974}}
        restore.apply_compaction_settings(settings, 0, 0)
        self.assertNotIn("compaction", settings)

    def test_a_users_own_compaction_block_is_left_alone(self):
        """Only remove what this harness derived. If the ceiling is off and the
        values do not match anything we would have written, they are the user's."""
        mine = {"compaction": {"enabled": False}}
        restore.apply_compaction_settings(mine, 0, 0)
        self.assertEqual(mine["compaction"], {"enabled": False})

    def test_floor_unknown_keeps_the_old_derivation(self):
        s = restore.compaction_settings_for(26000)
        self.assertEqual(s["keepRecentTokens"], 26000 // 8)



class TestHarnessConfigLocalOverride(unittest.TestCase):
    """Context limits are a property of the machine, not of the harness.

    usableContextTokens and perTurnPromptTokens depend on the model, the quant,
    the GPU and the installed skill set. Committing one machine's measurements
    into the shared config would ship them to everyone — the same rule that
    keeps machine paths out of the templates (CLAUDE.md, Forbidden
    Anti-Patterns). They belong in a gitignored local file, like settings.json
    and models.json already are.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "pi-config"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, data):
        with open(os.path.join(self.tmp, "pi-config", name), "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_local_file_overrides_shared_values(self):
        self._write("harness-config.json", {"usableContextTokens": 0, "promptProfile": "slim"})
        self._write("harness-config.local.json", {"usableContextTokens": 26000})
        cfg = restore.load_harness_config(self.tmp)
        self.assertEqual(cfg["usableContextTokens"], 26000)
        self.assertEqual(cfg["promptProfile"], "slim", "unrelated shared keys must survive")

    def test_without_a_local_file_the_shared_defaults_stand(self):
        self._write("harness-config.json", {"usableContextTokens": 0})
        cfg = restore.load_harness_config(self.tmp)
        self.assertEqual(cfg["usableContextTokens"], 0)

    def test_malformed_local_file_is_ignored_not_fatal(self):
        """A broken override must not stop someone from running restore."""
        self._write("harness-config.json", {"usableContextTokens": 0})
        with open(os.path.join(self.tmp, "pi-config", "harness-config.local.json"), "w") as f:
            f.write("{not json")
        cfg = restore.load_harness_config(self.tmp)
        self.assertEqual(cfg["usableContextTokens"], 0)

    def test_shared_config_ships_no_machine_measurements(self):
        """Guards the actual repo file, not a fixture: these two keys must stay
        at their inert defaults so a fresh clone changes nothing."""
        cfg = json.load(open(os.path.join(ROOT, "pi-config", "harness-config.json"), encoding="utf-8"))
        self.assertEqual(cfg.get("usableContextTokens", 0), 0)
        self.assertEqual(cfg.get("perTurnPromptTokens", 0), 0)


class TestCeilingSuggestion(unittest.TestCase):
    """Turning a measured ladder into a ceiling, so nobody has to eyeball it."""

    def test_picks_the_largest_fully_clean_rung(self):
        ladder = [(14000, 12, 12), (17000, 8, 8), (20000, 8, 8), (23000, 6, 8), (26000, 6, 8)]
        # Scaled so the trigger (ceiling - ceiling//4) lands on the 20,000 rung.
        self.assertEqual(restore.suggest_usable_ceiling(ladder), 26667)

    def test_returns_none_when_even_the_smallest_rung_fails(self):
        self.assertIsNone(restore.suggest_usable_ceiling([(14000, 5, 8), (17000, 4, 8)]))


    def test_ceiling_is_derived_so_the_trigger_lands_on_the_clean_rung(self):
        """The ceiling is not where the session sits — the trigger is.

        Compaction fires at ceiling - reserve (reserve = ceiling // 4), so
        returning the clean rung as the ceiling parks the trigger 25% BELOW the
        largest size known to work, throwing away headroom that was measured.
        """
        ladder = [(14000, 8, 8), (20100, 8, 8), (23083, 6, 8)]
        ceiling = restore.suggest_usable_ceiling(ladder)
        trigger = ceiling - restore.compaction_settings_for(ceiling)["reserveTokens"]
        self.assertGreaterEqual(trigger, 20100 * 0.95,
                                "the trigger should land at the largest clean rung, not below it")
        self.assertLessEqual(trigger, 23083, "and never above a rung known to degrade")

    def test_ignores_rungs_measured_with_too_few_samples(self):
        """One clean run at a big size is noise; the whole day proved that."""
        self.assertEqual(restore.suggest_usable_ceiling([(14000, 8, 8), (26000, 2, 2)]), 18667)


class TestCalibrateContext(unittest.TestCase):
    """The harness ships the measurement, not one machine's result."""

    def setUp(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import importlib
        self.cal = importlib.import_module("calibrate-context".replace("-", "_"))             if False else self._load()
        self.tmp = tempfile.mkdtemp()

    def _load(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "calibrate_context", os.path.join(ROOT, "scripts", "calibrate-context.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_token_estimate_matches_pis_own_heuristic(self):
        """Pi estimates untokenized messages at chars/4; using a different rule
        would make our written number disagree with what Pi compares against."""
        self.assertEqual(self.cal.estimate_tokens("a" * 400), 100)
        self.assertEqual(self.cal.estimate_tokens(""), 0)

    def test_falls_back_to_the_estimate_without_a_server(self):
        tokens, how = self.cal.count_tokens("x" * 800, None)
        self.assertEqual(tokens, 200)
        self.assertIn("estimate", how)

    def test_unreachable_server_is_not_fatal(self):
        self.assertIsNone(self.cal.tokenize_via_server("hi", "http://127.0.0.1:1"))

    def test_write_local_preserves_unrelated_keys(self):
        path = os.path.join(self.tmp, "local.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"somethingElse": True}, f)
        self.cal.LOCAL_CONFIG = path
        self.cal.write_local({"perTurnPromptTokens": 15287})
        data = json.load(open(path, encoding="utf-8"))
        self.assertTrue(data["somethingElse"])
        self.assertEqual(data["perTurnPromptTokens"], 15287)


if __name__ == "__main__":
    unittest.main()
