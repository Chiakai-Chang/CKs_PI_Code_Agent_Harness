import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestCaseAutonomousExecutionAddendum(unittest.TestCase):
    ADDENDUM = "pi-rules/case-autonomous-execution.md"

    def test_addendum_file_exists_with_required_sections(self):
        c = read(self.ADDENDUM)
        self.assertIn("DONE 閘門鬆綁", c)
        self.assertIn("強制復盤", c)
        self.assertIn("連續執行授權", c)
        self.assertIn("retro.md", c)
        self.assertIn("learnings.md", c)
        self.assertIn("create_subtask", c)

    def test_addendum_does_not_require_human_chat_approval(self):
        c = read(self.ADDENDUM)
        self.assertIn("不需要等待人類在 chat 中", c)

    def test_addendum_does_not_force_cross_model(self):
        c = read(self.ADDENDUM)
        # 必須明確允許同模型新 context，不能只有跨模型選項
        self.assertIn("同一個 AI", c)

    def test_addendum_preserves_escalation_semantics(self):
        c = read(self.ADDENDUM)
        self.assertIn("ESCALATED", c)


if __name__ == "__main__":
    unittest.main()
