import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestEvidenceBasedCompletionPrinciple(unittest.TestCase):
    """The 實測有證據 (evidence-based completion) principle is this repo's soul.
    It must stay in the always-loaded governing docs — AGENTS.md for Pi agents,
    CLAUDE.md for Claude agents — so every agent sees it every session. Guard it
    so it cannot be silently dropped."""

    def test_principle_in_pi_agents_rules(self):
        c = read("pi-rules/AGENTS.md")
        self.assertIn("實測有證據", c)
        # the core injunction and the cold-path lesson must both survive
        self.assertIn("冷測", c)
        # numbers/claims in reports & commit messages must come from a real run
        self.assertIn("先跑再寫", c)
        # the anti-fabrication floor — the worst observed failure (fabricated
        # field tests / venues / ROI presented as real). Must not be dropped.
        self.assertIn("不捏造", c)

    def test_top_iron_rules_banner_present(self):
        """The 3 hardest disciplines (no language drift / no fabrication /
        plan-first + stay-in-project) are front-loaded as a top banner so a
        weak model sees them first. Guard the banner so it isn't dropped."""
        c = read("pi-rules/AGENTS.md")
        self.assertIn("最高鐵律", c)
        # banner must sit before the numbered sections (front placement is the point)
        self.assertLess(c.index("最高鐵律"), c.index("## 0."))

    def test_principle_in_claude_md(self):
        c = read("CLAUDE.md")
        self.assertIn("Evidence-Based Completion", c)
        self.assertIn("實測有證據", c)


class TestMethodologyFirstPrinciple(unittest.TestCase):
    """Methodology-first routing (process skill before domain skill) is the
    other half of the repo's soul — it stops the many bundled methodology
    skills from being unused shells. Guard it in the always-loaded docs, and
    keep the routing honest: every skill it names must be a real, wired skill."""

    # Every name here is a verified-loadable skill (checked against the skills'
    # SKILL.md name: frontmatter). NB "qiushi" is NOT a skill — that submodule
    # ships contradiction-analysis et al.; "evolver" loads as capability-evolver.
    WIRED = ("brainstorming", "planning-with-files", "systematic-debugging",
             "test-driven-development", "thinking-frameworks", "mece-autopilot",
             "contradiction-analysis", "case-framework")

    def test_methodology_routing_in_agents(self):
        c = read("pi-rules/AGENTS.md")
        self.assertIn("方法論優先", c)
        # the routing must name real methodology skills, not vague prose
        for s in self.WIRED:
            self.assertIn(s, c, "AGENTS.md §10 must route to the wired skill %s" % s)

    def test_no_zombie_harness_config_keys(self):
        """CLAUDE.md forbids zombie config. Three keys had already gone zombie —
        enableUniversalTagTransformer and enableSelfHealingLoopGuard were
        documented in README as the fix for tag deadlock while no code read
        either, and enableTasteBridge was read against a path that never
        existed. A user following the documented remedy saw nothing change and
        concluded the harness was unfixable. Every declared key must have a
        consumer."""
        import json as _json
        with open(os.path.join(ROOT, "pi-config", "harness-config.json"), encoding="utf-8") as f:
            cfg = _json.load(f)
        sources = []
        for sub in ("pi-extensions", "scripts", "pi-skills"):
            for dp, dn, fn in os.walk(os.path.join(ROOT, sub)):
                for name in fn:
                    if name.endswith((".ts", ".py", ".js", ".sh")):
                        try:
                            with open(os.path.join(dp, name), encoding="utf-8", errors="replace") as f:
                                sources.append(f.read())
                        except OSError:
                            pass
        blob = "\n".join(sources)
        # Match an ACCESS shape, not a bare word. A plain substring search
        # passes any key whose name happens to appear anywhere — "description"
        # sailed through because unrelated tool definitions use that word,
        # which is the same false-negative hole this test exists to close.
        import re as _re
        zombies = []
        for key in cfg:
            if key.startswith(("_", "$")):
                continue  # documentation-only keys, by convention
            k = _re.escape(key)
            accessed = _re.search(r'["\']%s["\']|\.%s\b|\[%s\]' % (k, k, k), blob)
            if not accessed:
                zombies.append(key)
        self.assertEqual(
            zombies, [],
            "harness-config.json declares keys no code reads: %s. Either wire "
            "them up, delete them, or prefix with '_' if documentation-only — a "
            "config knob that does nothing is worse than no knob, because the "
            "docs tell users to turn it." % zombies,
        )

    def test_section_numbering_has_no_gaps(self):
        """Section numbers are cited across the repo (AGENTS.md §4, §9, §10) and
        by the bridges' injected text. A gap means content sits under a heading
        that does not describe it — the shell/path rules spent time buried under
        the '0. Language & Locale' heading, where a model scanning headings for
        'do not use PowerShell' would never look."""
        import re
        c = read("pi-rules/AGENTS.md")
        nums = [int(n) for n in re.findall(r"^## (\d+)\.", c, re.M)]
        self.assertEqual(nums, list(range(nums[0], nums[0] + len(nums))),
                         "AGENTS.md section numbers must be contiguous, got %s" % nums)

    def test_methodology_first_in_claude_md(self):
        c = read("CLAUDE.md")
        self.assertIn("Methodology-First", c)


class TestDocumentedChecksRunInCI(unittest.TestCase):
    """README and CLAUDE.md present these as the health checks. CI ran none of
    them — a broken bridge registration or a machine path committed into the
    tracked config template would have gone green."""

    def setUp(self):
        with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as f:
            self.ci = f.read()

    def test_every_documented_check_is_wired_into_ci(self):
        with open(os.path.join(ROOT, "CLAUDE.md"), encoding="utf-8") as f:
            claude = f.read()
        import re as _re
        documented = set(_re.findall(r"python (scripts/[a-z-]+\.py)", claude))
        # measure-triggers runs the local model for minutes; deliberately not CI.
        documented.discard("scripts/measure-triggers.py")
        documented.discard("scripts/setup.py")
        missing = [c for c in sorted(documented) if c not in self.ci]
        self.assertEqual(missing, [], "documented checks absent from CI: %s" % missing)


if __name__ == "__main__":
    unittest.main()
