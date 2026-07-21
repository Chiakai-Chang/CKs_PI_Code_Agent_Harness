import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


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
