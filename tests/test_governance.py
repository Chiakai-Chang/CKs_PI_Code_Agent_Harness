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

    def test_methodology_first_in_claude_md(self):
        c = read("CLAUDE.md")
        self.assertIn("Methodology-First", c)


if __name__ == "__main__":
    unittest.main()
