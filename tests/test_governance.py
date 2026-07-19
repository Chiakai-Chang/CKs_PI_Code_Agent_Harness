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
