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
        self.assertIn("疏漏與不當", c)
        self.assertIn("可優化之處", c)
        self.assertIn("收穫", c)
        self.assertIn("回饋 CASE", c)

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

    def test_addendum_has_plan_self_review_gate(self):
        """2026-07-22 addition: role.md/recipe.md treated as this task's own
        binding local constitution, plan reviewed (DoD coverage, constraint
        conflicts, unsupported assumptions) before any input is read or code
        is written, escalating early on a genuine gap instead of after
        wasted execution effort. Mirrors the same-day upstream contribution
        to external/Local-Agent-Workspace's for_agents.md §6 step 4 / §19.D,
        since case-bridge injects this addendum but never injects
        for_agents.md itself."""
        c = read(self.ADDENDUM)
        self.assertIn("Self-Review", c)
        self.assertIn("小憲法", c)
        self.assertIn("planning.md", c)
        self.assertIn("escalate_issue", c)


class TestCaseBridgeInjectsAddendum(unittest.TestCase):
    IDX = "pi-extensions/case-bridge/index.ts"

    def test_reads_addendum_from_pi_rules(self):
        c = read(self.IDX)
        self.assertIn('"pi-rules"', c)
        self.assertIn('"case-autonomous-execution.md"', c)

    def test_injects_addendum_with_marker(self):
        c = read(self.IDX)
        self.assertIn("BEGIN C.A.S.E. HARNESS ADDENDUM", c)
        self.assertIn("END C.A.S.E. HARNESS ADDENDUM", c)

    def test_addendum_only_injected_for_case_projects(self):
        c = read(self.IDX)
        # 疊加邏輯必須在 isCaseProject(ctx.cwd) 的 if 區塊內，
        # 用既有 constitution/roadmap 注入區塊做參照點：
        # BEGIN 標記必須出現在 "if (isCaseProject(ctx.cwd))" 之後。
        idx_if = c.index("if (isCaseProject(ctx.cwd))")
        idx_marker = c.index("BEGIN C.A.S.E. HARNESS ADDENDUM")
        self.assertGreater(idx_marker, idx_if)


if __name__ == "__main__":
    unittest.main()
