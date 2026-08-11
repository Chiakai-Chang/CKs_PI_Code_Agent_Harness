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


GUARD_MOD = ROOT / "pi-extensions" / "case-bridge" / "task-queue-guard.ts"


def run_guard(script):
    """Drives the real TaskQueueGuard through its public entry point.

    The wiring used to be checked by asserting that the source text contained
    "missingDodArtifacts(". It did contain it — and the guard was dead anyway,
    because the call named `_cwd`, an identifier that exists only on `check()`
    and not on the `evaluate()` body where the call sits. The ReferenceError was
    swallowed by a nearby catch written for unparsable recipes, so REVIEW was
    allowed with no artifacts and every test stayed green. Assert on behaviour.
    """
    driver = ROOT / "tests" / ".tmp_queue_guard.mjs"
    url = "file:///" + str(GUARD_MOD).replace("\\", "/")
    driver.write_text("import {TaskQueueGuard} from %s;\n%s" % (json.dumps(url), script),
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


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTaskLevelMethodology(unittest.TestCase):
    """Global had planning and methodology routing; a claimed task had a form.

    Found 2026-08-10 when the owner asked whether a task taken from the queue
    executes with planning and the superpowers methodology. It did not. The
    router classifies the USER's message at `before_agent_start` — a queue run's
    user message is "繼續", while the multi-step work is described in the task's
    recipe.md, which nothing read. The phase gate's PLAN refusal says "write
    planning.md with steps, files and a verification method", which is a FORM,
    not a METHOD: it never names systematic-debugging or brainstorming.

    So the methodology line rides the task constitution, at the claim, on the
    channel already proven to deliver."""

    def line(self, objective):
        return run_js("process.stdout.write(JSON.stringify(m.methodology(%s)));"
                      % json.dumps(objective))

    ROUTED = "這個任務的形狀適合先載入"

    def assertRoutedTo(self, objective, skill):
        """Routed, not merely mentioned.

        The first version asserted only that the skill name appeared, and the
        fallback line names ALL THREE — so deleting the routing rule left the
        test green. A check that cannot tell the two apart is not checking."""
        out = self.line(objective)
        self.assertIn(self.ROUTED, out,
                      "fell through to the generic rule instead of routing")
        head = out.split(self.ROUTED, 1)[1].split("**方法先於動手", 1)[0]
        self.assertIn(skill, head, "routed to something else: %r" % head)

    def test_a_bug_task_names_systematic_debugging(self):
        self.assertRoutedTo("修復冷啟動的 ENOENT 錯誤", "systematic-debugging")

    def test_a_research_task_names_brainstorming(self):
        self.assertRoutedTo("研究三個競品的定價並比較", "brainstorming")

    def test_an_implementation_task_names_tdd(self):
        self.assertRoutedTo("實作一個新的佇列推進器", "test-driven-development")

    def test_an_unmatched_task_does_not_claim_to_have_routed(self):
        """The counterpart: the generic line must not pretend it picked one."""
        self.assertNotIn(self.ROUTED, self.line("清點 src/ 底下所有模組並記錄數量"))

    def test_an_unmatched_task_still_gets_the_routing_rule(self):
        """Naming nothing would be worse than naming everything: the model would
        read silence as "no method needed". When no signal matches, the full
        routing rule goes out instead."""
        out = self.line("清點 src/ 底下所有模組並記錄數量")
        for skill in ("systematic-debugging", "brainstorming",
                      "test-driven-development"):
            self.assertIn(skill, out)

    def test_the_planning_requirement_is_never_conditional(self):
        """The phase gate refuses deliverables without planning.md + Self-Review
        whatever the task looks like, so this half must not depend on a keyword."""
        for objective in ("修復錯誤", "研究競品", "實作功能", "清點檔案", ""):
            with self.subTest(objective=objective):
                out = self.line(objective)
                self.assertIn("planning.md", out)
                self.assertIn("Self-Review", out)

    def test_it_names_the_right_plan_file(self):
        """The router's own routine says `task_plan.md`, which nothing in a
        C.A.S.E. project reads. Pointing a claimed task at the wrong artifact is
        the confusion this whole change exists to end."""
        out = self.line("研究競品")
        self.assertIn("task_plan.md", out)
        self.assertIn("不是", out)

    def test_it_reaches_the_injected_block(self):
        """A pure function nobody calls is this repo's most repeated defect."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        task = tmp / "Task_001_probe"
        task.mkdir()
        (task / "recipe.md").write_text(
            "## Objective" + chr(10) + "修復冷啟動的 ENOENT 錯誤" + chr(10),
            encoding="utf-8")
        self.assertIn("systematic-debugging", load(task)["text"])


class TestTheRouterYieldsInCaseProjects(unittest.TestCase):
    """Two planning systems that could not see each other.

    `hasAnyPlan` looks for `task_plan.md`; a C.A.S.E. task writes `planning.md`
    inside its package. So the routine fired in queue projects and pointed at an
    artifact nothing there reads, while one stray task_plan.md at a project root
    suppressed it for every task in the queue. The router now stands down in a
    C.A.S.E. project — the same shape as the phase gate yielding to containment:
    whoever has the more specific complaint speaks, and only one of them can."""

    def setUp(self):
        self.src = (ROOT / "pi-extensions" / "task-shape-bridge"
                    / "index.ts").read_text(encoding="utf-8")

    def test_the_router_checks_for_a_case_project(self):
        self.assertIn("isCaseProject(ctx.cwd)", self.src)

    def test_it_yields_before_arming_the_routine(self):
        """Standing down after `armed = buildRoutine(...)` would still deliver."""
        head = self.src.split("armed = buildRoutine", 1)[0]
        self.assertIn("isCaseProject(ctx.cwd)) return", head)

    def test_the_classifier_is_not_duplicated(self):
        """The predicate is two filesystem checks; the classifier is not copied.
        Duplicating `shape.ts` cost this repo a commit already."""
        plan = (ROOT / "pi-extensions" / "task-shape-bridge"
                / "plan.ts").read_text(encoding="utf-8")
        self.assertIn("export function isCaseProject", plan)
        for owned_by_shape in ("classifyRequest", "deliverables >="):
            self.assertNotIn(owned_by_shape, plan)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestTheDodArtifactCheck(unittest.TestCase):
    """A task reached REVIEW with nothing in it while every guard passed.

    Session 019febe9, in order: `write output.md` refused by the phase gate (not
    claimed yet), `status.txt = DONE` refused by the transition guard, IN_PROGRESS
    allowed, `DONE` refused again, `REVIEW` allowed. Final state REVIEW with no
    output.md and no planning.md — and the refused call had carried the complete
    report, which was never written again.

    It tried twice for DONE, was refused twice, and took the legal road. The legal
    road asked for no artifacts. REVIEW is what summons a human under Path A, so
    this is the difference between accepting work and accepting an empty folder."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.task = self.tmp / "Task_001"
        self.task.mkdir()

    def recipe(self, dod):
        (self.task / "recipe.md").write_text(
            "## Objective" + chr(10) + "x" + chr(10) * 2 +
            "## Local Definition of Done (DoD)" + chr(10) + dod + chr(10),
            encoding="utf-8")

    def missing(self):
        return run_js(
            "import {existsSync} from 'node:fs';" + chr(10) +
            "process.stdout.write(JSON.stringify("
            "m.missingDodArtifacts(%s, %s, existsSync)));"
            % (json.dumps(str(self.task)), json.dumps(str(self.tmp))))

    def test_a_named_file_that_does_not_exist_is_reported(self):
        self.recipe("- [ ] output.md 列出每個模組的 retries 值")
        self.assertEqual(self.missing(), ["output.md"])

    def test_the_same_file_named_twice_is_reported_once(self):
        self.recipe("- [ ] output.md 列出數值" + chr(10) + "- [ ] output.md 指出差異")
        self.assertEqual(self.missing(), ["output.md"])

    def test_once_written_it_passes(self):
        self.recipe("- [ ] output.md 列出每個模組的 retries 值")
        (self.task / "output.md").write_text("x", encoding="utf-8")
        self.assertEqual(self.missing(), [])

    def test_a_dod_that_names_no_file_asks_for_nothing(self):
        """"run the tests" is not an artifact. Turning every DoD line into a
        required file would refuse tasks that owe no document."""
        self.recipe("- [ ] 跑 python -m unittest 並貼上輸出")
        self.assertEqual(self.missing(), [])

    def test_a_package_with_no_recipe_is_not_held_to_one(self):
        """Fails open. A task that never said what it owes cannot be judged."""
        self.assertEqual(self.missing(), [])

    def test_a_file_that_exists_elsewhere_in_the_workspace_passes(self):
        """A DoD may cite an input it did not create."""
        self.recipe("- [ ] 讀 roadmap.md 後更新 notes.md")
        (self.tmp / "roadmap.md").write_text("x", encoding="utf-8")
        self.assertEqual(self.missing(), ["notes.md"])

    def test_a_chinese_dod_heading_is_recognised(self):
        """A project writing its recipes in Chinese heads the section 驗收. The
        mutation sweep survived removing that fallback — checking only the
        English spelling and shipping is how the skill catalogue ended up
        unreadable to half the projects that had one."""
        (self.task / "recipe.md").write_text(
            "## 目標" + chr(10) + "調查" + chr(10) * 2 +
            "## 驗收" + chr(10) + "- [ ] report.md 列出結果" + chr(10),
            encoding="utf-8")
        self.assertEqual(self.missing(), ["report.md"])

    def test_the_package_s_own_files_are_never_demanded(self):
        """status.txt is the file being written at that moment; recipe and role
        are inputs. Demanding them would refuse every REVIEW."""
        self.recipe("- [ ] status.txt 設為 REVIEW" + chr(10) + "- [ ] 依 role.md 的角色行事")
        self.assertEqual(self.missing(), [])


class TestTheDodGuardBlocksInPractice(unittest.TestCase):
    """Run 3 of T-A1 (2026-08-11) reached REVIEW with no output.md while 1289
    tests were green. These drive `check()` on a real folder, which is the only
    thing that would have caught it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # The name must match ^Task_(\d+)_ — `Task_001` alone does not, and a
        # fixture that misses it exercises nothing at all: every status write
        # was allowed, including "bogus". Caught while diagnosing run 3.
        self.task = self.tmp / "02_Task_Queue" / "Task_001_Drift"
        self.task.mkdir(parents=True)
        (self.task / "recipe.md").write_text(
            "## Local Definition of Done (DoD)" + chr(10) +
            "- [ ] `output.md` 存在" + chr(10), encoding="utf-8")
        (self.task / "status.txt").write_text("IN_PROGRESS" + chr(10), encoding="utf-8")

    def review(self, cwd):
        return run_guard(
            "const g = new TaskQueueGuard();" + chr(10) +
            "const r = g.check('write', {path: %s, content: 'REVIEW\\n'}, %s);" % (
                json.dumps(str(self.task / "status.txt")), json.dumps(cwd)) + chr(10) +
            "process.stdout.write(JSON.stringify(r === null ? null : r.reason));")

    def test_review_is_refused_when_the_named_artifact_is_absent(self):
        r = self.review(str(self.tmp))
        self.assertIsNotNone(r, "REVIEW was allowed with output.md absent")
        self.assertIn("output.md", r)

    def test_review_is_allowed_once_the_artifact_exists(self):
        (self.task / "output.md").write_text("x", encoding="utf-8")
        self.assertIsNone(self.review(str(self.tmp)))

    def test_it_still_refuses_when_no_cwd_is_supplied(self):
        """Pi does not always hand the guard a cwd. The artifact sits in the task
        folder here, so the task folder alone is enough to decide."""
        self.assertIsNotNone(self.review(None))

    def test_an_unparsable_recipe_does_not_stop_the_machine(self):
        (self.task / "recipe.md").write_text("no dod here", encoding="utf-8")
        self.assertIsNone(self.review(str(self.tmp)))