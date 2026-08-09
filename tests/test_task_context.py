"""The task's own constitution, loaded when the task is claimed.

Every C.A.S.E. task package ships `role.md` and a `recipe.md` carrying an
Objective and a Local Definition of Done. Nothing in this harness had ever loaded
them: searching the repo for `role.md` found a line in `phase-gate.ts` SUGGESTING
the model go read it, and a table in a docs page. A suggestion loses to the
moment of action every time it has been measured here.

They cannot arrive later either. Moving to the next task uses
`sendMessage({ customType }, { deliverAs: "followUp", triggerTurn: true })`, and
session 019fcf32 recorded that custom message sitting between two assistant turns
with no user message between — so `before_agent_start`, which fires "after user
submits prompt", never runs again. Every task in a queue run shares one prompt
cycle.

So the tests below are mostly about the boundary: it must fire once per TASK (not
once per session, because a queue run claims several with different rules), it
must not fire on a refused call, and it must stay silent rather than inject an
empty shell when a package carries no local rules.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = ROOT / "pi-extensions" / "case-bridge" / "task-context.ts"
INDEX = ROOT / "pi-extensions" / "case-bridge" / "index.ts"


def _node_major():
    if not shutil.which("node"):
        return 0
    try:
        out = subprocess.run(["node", "--version"], capture_output=True,
                             text=True, timeout=30).stdout
    except Exception:
        return 0
    m = re.match(r"v(\d+)", out.strip())
    return int(m.group(1)) if m else 0


NODE_OK = _node_major() >= 22

ROLE = ("# Role\n\nYou are a Principal Security Architect and AI Agent Framework "
        "Researcher. Your role is to analyze foreign repositories.\n")
RECIPE = """# Task Recipe: Analyze Foreign Repositories

## Objective
Clone, analyze, and extract lessons from six target repositories.

## Input Sources
- https://example.invalid/one
- https://example.invalid/two

## Local Definition of Done (DoD)
- [ ] Clone all 6 repositories to `external_references/`.
- [ ] Extract key software engineering patterns applicable to C.A.S.E.
"""


def run_js(script):
    driver = ROOT / "tests" / ".tmp_task_context.mjs"
    url = "file:///" + str(MOD).replace("\\", "/")
    driver.write_text("import * as m from %s;\n%s" % (json.dumps(url), script),
                      encoding="utf-8")
    try:
        p = subprocess.run(["node", str(driver)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(ROOT),
                           timeout=120)
        if p.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        if driver.exists():
            driver.unlink()


def load(task_dir):
    return run_js("process.stdout.write(JSON.stringify("
                  "m.localConstitution(%s)));" % json.dumps(str(task_dir)))


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestSectionParsing(unittest.TestCase):
    def test_extracts_a_named_section_without_its_heading(self):
        out = run_js("process.stdout.write(JSON.stringify("
                     "m.section(%s, 'objective')));" % json.dumps(RECIPE))
        self.assertIn("Clone, analyze, and extract", out)
        self.assertNotIn("## Objective", out)

    def test_a_section_stops_at_the_next_heading_of_the_same_level(self):
        """Objective must not swallow Input Sources."""
        out = run_js("process.stdout.write(JSON.stringify("
                     "m.section(%s, 'objective')));" % json.dumps(RECIPE))
        self.assertNotIn("example.invalid", out)

    def test_a_deeper_heading_stays_inside_the_section(self):
        """Ending on ANY heading was the first version, and it cut a Local DoD
        in half at its own `### Evidence` sub-heading."""
        doc = ("## Local Definition of Done\n- [ ] first\n\n"
               "### Evidence\n- [ ] the command output\n\n## Next\nunrelated\n")
        out = run_js("process.stdout.write(JSON.stringify("
                     "m.section(%s, 'local definition of done')));" % json.dumps(doc))
        self.assertIn("the command output", out)
        self.assertNotIn("unrelated", out)

    def test_a_heading_with_a_parenthetical_still_matches(self):
        """The vendored template writes `## Local Definition of Done (DoD)`."""
        out = run_js("process.stdout.write(JSON.stringify("
                     "m.section(%s, 'local definition of done')));" % json.dumps(RECIPE))
        self.assertIn("Clone all 6 repositories", out)

    def test_a_top_level_heading_section_is_found(self):
        """`# Objective` at depth 1, not just `## Objective`. The mutation sweep
        survived turning the depth test into `depth > 1`, which silently drops
        every section written with a single hash."""
        doc = chr(10).join(["# Objective", "ship the thing", "",
                            "# Next", "unrelated", ""])
        out = run_js("process.stdout.write(JSON.stringify("
                     "m.section(%s, 'objective')));" % json.dumps(doc))
        self.assertEqual(out, "ship the thing")

    def test_an_empty_name_matches_nothing(self):
        """`title.startsWith("")` is true for every heading, so without the
        guard an empty name returns the whole document from its first heading
        onward. The mutation sweep survived flipping that guard's `||` to `&&`,
        which is exactly this hole."""
        out = run_js("process.stdout.write(JSON.stringify("
                     "m.section(%s, '')));" % json.dumps(RECIPE))
        self.assertEqual(out, "")

    def test_a_missing_section_is_empty_not_an_error(self):
        out = run_js("process.stdout.write(JSON.stringify("
                     "m.section(%s, 'nonexistent')));" % json.dumps(RECIPE))
        self.assertEqual(out, "")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestLocalConstitution(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.task = self.tmp / "Task_001_probe"
        self.task.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_full(self):
        (self.task / "role.md").write_text(ROLE, encoding="utf-8")
        (self.task / "recipe.md").write_text(RECIPE, encoding="utf-8")

    def test_carries_the_role_the_objective_and_the_dod(self):
        self.write_full()
        out = load(self.task)
        self.assertIn("Principal Security Architect", out["text"])
        self.assertIn("Clone, analyze, and extract", out["text"])
        self.assertIn("Clone all 6 repositories", out["text"])
        self.assertEqual(sorted(out["sources"]), ["recipe.md", "role.md"])

    def test_labelled_so_it_is_not_read_as_tool_output(self):
        self.write_full()
        self.assertIn("[C.A.S.E.]", load(self.task)["text"])

    def test_an_empty_package_stays_silent(self):
        """An injected header with nothing under it teaches the model that this
        channel carries noise, and the next real one gets skimmed."""
        self.assertIsNone(load(self.task))

    def test_a_package_with_only_a_role_still_speaks(self):
        (self.task / "role.md").write_text(ROLE, encoding="utf-8")
        out = load(self.task)
        self.assertEqual(out["sources"], ["role.md"])
        self.assertIn("Principal Security Architect", out["text"])

    def test_a_recipe_with_no_recognised_sections_stays_silent(self):
        (self.task / "recipe.md").write_text("# Recipe\n\nsome prose\n",
                                             encoding="utf-8")
        self.assertIsNone(load(self.task))

    def test_chinese_headings_are_recognised(self):
        """Checking only the English spelling and shipping is how the skill
        catalogue ended up unreadable to half the projects that had one."""
        (self.task / "recipe.md").write_text(
            "# 任務\n\n## 目標\n把三個競品的定價整理成表格。\n\n"
            "## 驗收\n- [ ] 表格寫進 output.md\n", encoding="utf-8")
        out = load(self.task)
        self.assertIn("競品的定價", out["text"])
        self.assertIn("表格寫進 output.md", out["text"])

    def test_an_objective_only_recipe_still_credits_recipe_md(self):
        """With a DoD present the other branch pushes the source anyway, so this
        is the only shape that can observe the objective branch's own push. The
        mutation sweep survived removing its negation until this existed."""
        (self.task / "recipe.md").write_text(
            "## Objective" + chr(10) + "do the thing" + chr(10), encoding="utf-8")
        out = load(self.task)
        self.assertEqual(out["sources"], ["recipe.md"])
        self.assertIn("do the thing", out["text"])

    def test_a_missing_directory_is_silent_not_an_error(self):
        self.assertIsNone(load(self.tmp / "does-not-exist"))

    def test_the_block_is_capped(self):
        """It rides a tool result the model is already reading. A block that
        buries the tool's own output competes with the thing it is attached to."""
        (self.task / "role.md").write_text("# Role\n\n" + "長" * 5000,
                                           encoding="utf-8")
        (self.task / "recipe.md").write_text(
            "## Objective\n" + "目" * 5000 + "\n\n## 驗收\n" + "驗" * 5000,
            encoding="utf-8")
        cap = run_js("process.stdout.write(JSON.stringify(m.MAX_TASK_CONTEXT_CHARS));")
        out = load(self.task)
        self.assertLessEqual(len(out["text"]), cap + 20)

    def test_an_english_only_recipe_keeps_both_sections(self):
        """Pins the fallback chains. Breaking either one drops a section from a
        template that is otherwise perfectly ordinary."""
        (self.task / "recipe.md").write_text(RECIPE, encoding="utf-8")
        text = load(self.task)["text"]
        self.assertIn("Clone, analyze, and extract", text)
        self.assertIn("Clone all 6 repositories", text)

    def test_a_dod_heading_without_the_word_local_is_found(self):
        (self.task / "recipe.md").write_text(
            chr(10).join(["## Objective","do it","","## Definition of Done","- [ ] proof",""]),
            encoding="utf-8")
        self.assertIn("proof", load(self.task)["text"])

    def test_truncation_keeps_the_head_from_the_first_character(self):
        """`slice(0, max)` surviving as `slice(1, max)` drops the first
        character of a role or an objective, invisibly."""
        (self.task / "role.md").write_text("# Role" + chr(10)*2 + "Z" + "長" * 5000,
                                           encoding="utf-8")
        self.assertIn("Z", load(self.task)["text"])

    def test_a_section_exactly_at_the_cap_is_not_marked_truncated(self):
        """The boundary. `<=` surviving as `<` marks an intact section as cut."""
        caps = run_js("process.stdout.write(JSON.stringify("
                      "[m.MAX_TASK_CONTEXT_CHARS]));")
        (self.task / "recipe.md").write_text(
            "## Objective" + chr(10) + "x" * 600 + chr(10), encoding="utf-8")
        text = load(self.task)["text"]
        self.assertNotIn("截斷", text)
        self.assertLessEqual(len(text), caps[0])

    def test_the_total_cap_is_exact(self):
        """Pins MAX_TASK_CONTEXT_CHARS. Without this, 1200 -> 1201 changes what
        the model receives and no test notices."""
        (self.task / "role.md").write_text("# Role" + chr(10)*2 + "長" * 5000,
                                           encoding="utf-8")
        (self.task / "recipe.md").write_text(
            "## Objective" + chr(10) + "目"*5000 + chr(10)*2 + "## 驗收" + chr(10) + "驗"*5000,
            encoding="utf-8")
        cap = run_js("process.stdout.write(JSON.stringify(m.MAX_TASK_CONTEXT_CHARS));")
        text = load(self.task)["text"]
        # Length of the whole block, not a split on the marker: the per-section
        # caps put their own marker inside the text first, so splitting finds
        # the role's truncation rather than the total's.
        marker = " …(截斷)"
        self.assertTrue(text.endswith(marker), "the total was not clipped")
        self.assertEqual(len(text) - len(marker), cap)
        self.assertEqual(cap, 1200)

    def test_the_role_cap_is_exact(self):
        """Pins MAX_ROLE_CHARS via the only thing that can observe it."""
        (self.task / "role.md").write_text("# Role" + chr(10)*2 + "長" * 5000,
                                           encoding="utf-8")
        text = load(self.task)["text"]
        role_body = text.split("**你在這個任務裡的角色**")[1].split(" …(截斷)")[0]
        self.assertEqual(len(role_body.strip()), 500)

    def test_the_section_cap_is_exact(self):
        """Pins MAX_SECTION_CHARS."""
        (self.task / "recipe.md").write_text(
            "## Objective" + chr(10) + "目"*5000 + chr(10), encoding="utf-8")
        text = load(self.task)["text"]
        body = text.split("**這個任務的目標**")[1].split(" …(截斷)")[0]
        self.assertEqual(len(body.strip()), 600)

    def test_it_demands_evidence_the_way_the_repo_does(self):
        """The footer is the one instruction here, and it is the repo's own
        standing rule rather than a new one invented for this channel."""
        self.write_full()
        self.assertIn("Local DoD", load(self.task)["text"])
        self.assertIn("實際跑過", load(self.task)["text"])


class TestWiring(unittest.TestCase):
    """A pure module nobody calls is the defect this repo ships most often —
    an undeclared variable in a bridge handler once passed 774 tests, three
    checks and a byte-identical install."""

    def setUp(self):
        self.src = INDEX.read_text(encoding="utf-8")

    def test_bridge_imports_and_calls_it(self):
        self.assertIn("task-context.ts", self.src)
        self.assertIn("localConstitution(", self.src)

    def test_delivered_on_the_claim_via_the_tool_result_channel(self):
        handler = self.src.split('pi.on("tool_result"')[1]
        self.assertIn("claimedTaskDir(", handler)
        self.assertIn("localConstitution(", handler)
        self.assertRegex(handler, r"content:\s*\[\.\.\.\(event\.content")

    def test_both_riders_share_one_return(self):
        """Returning on the first would starve the second in silence."""
        handler = self.src.split('pi.on("tool_result"')[1]
        self.assertIn("blocks.push", handler)
        self.assertIn("phaseNotice.afterToolResult", handler)

    def test_sent_once_per_task_not_once_per_session(self):
        """A queue run claims several tasks and each has different rules."""
        self.assertIn("taskContextSent", self.src)
        self.assertIn("taskContextSent.add(", self.src)
        self.assertIn("taskContextSent.clear()", self.src)

    def test_the_claim_detector_is_not_duplicated(self):
        """One detector for one event. `uninstall.py` managed five bridges while
        `restore.py` managed eleven, and seven kept loading forever."""
        notice = (ROOT / "pi-extensions" / "case-bridge" /
                  "phase-notice.ts").read_text(encoding="utf-8")
        self.assertEqual(notice.count("export function claimedTaskDir"), 1)
        self.assertIn("claimedTaskDir(queueDir, toolName, input, isError)", notice)


if __name__ == "__main__":
    unittest.main()
