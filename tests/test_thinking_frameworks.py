import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = "pi-skills/optional/thinking-frameworks/SKILL.md"
RATIONALE = "pi-skills/optional/thinking-frameworks/RATIONALE.md"


def read_file(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
        return f.read()


class TestThinkingFrameworks(unittest.TestCase):
    def test_skill_exists_and_named(self):
        self.assertIn("name: thinking-frameworks", read_file(SKILL))

    def test_seven_frameworks_present(self):
        c = read_file(SKILL)
        for kw in ["反演", "基準率", "二階", "機會成本", "第一性", "偏誤", "可證偽"]:
            self.assertIn(kw, c, f"missing framework: {kw}")

    def test_division_of_labor(self):
        c = read_file(SKILL).lower()
        self.assertIn("mece", c)
        self.assertIn("qiushi", c)

    def test_boundary_present(self):
        c = read_file(SKILL)
        self.assertIn("不冒名", c)
        self.assertIn("純推理工具", c)
        self.assertIn("不提供投資", c)

    def test_no_impersonation_patterns(self):
        c = read_file(SKILL)
        for bad in ["我是巴菲特", "作為巴菲特", "扮演巴菲特",
                    "You are Warren Buffett", "act as "]:
            self.assertNotIn(bad, c, f"impersonation pattern present: {bad}")

    def test_no_machine_paths(self):
        for rel in (SKILL, RATIONALE):
            self.assertIsNone(
                re.search(r"file:///[A-Za-z]:/|[A-Za-z]:/MyProject", read_file(rel)),
                f"{rel} has a machine-specific path",
            )


if __name__ == "__main__":
    unittest.main()
