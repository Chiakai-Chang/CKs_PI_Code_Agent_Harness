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

    def test_principle_in_claude_md(self):
        c = read("CLAUDE.md")
        self.assertIn("Evidence-Based Completion", c)
        self.assertIn("實測有證據", c)


if __name__ == "__main__":
    unittest.main()
