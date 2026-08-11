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


class TestGoverningDocsStayInSync(unittest.TestCase):
    """CLAUDE.md and pi-rules/AGENTS.md §9 are two renderings of one rule set,
    for two different agents. Nothing kept their contents level: the pair had
    already drifted (AGENTS.md carried the anti-fabrication floor, CLAUDE.md did
    not) and it took a human reading both to notice.

    The class above guards that the principle exists in each. This one guards the
    individual rules, which is where drift actually happens.

    Adding a rule to one doc means adding it to the other AND to this list. That
    is the point — the list is the thing that goes red.
    """

    # (what it is, marker in CLAUDE.md, marker in AGENTS.md)
    PAIRED_RULES = [
        ("cold-path testing", "Test the real entry path, cold", "冷測"),
        ("numbers come from a run", "come from a run at write-time", "先跑再寫"),
        ("restore before testing", "Pi runs installed copies", "Pi 跑的是安裝副本"),
        ("session log proves delivery", "~/.pi/agent/sessions", "~/.pi/agent/sessions"),
        ("contracts from the installed package", "installed package", "已安裝的套件"),
    ]

    def test_every_paired_rule_appears_in_both_governing_docs(self):
        claude = read("CLAUDE.md")
        agents = read("pi-rules/AGENTS.md")
        missing = []
        for name, claude_marker, agents_marker in self.PAIRED_RULES:
            if claude_marker not in claude:
                missing.append("CLAUDE.md is missing %r (%s)" % (claude_marker, name))
            if agents_marker not in agents:
                missing.append("AGENTS.md is missing %r (%s)" % (agents_marker, name))
        self.assertEqual(missing, [])


class TestForkCopyIsNotCitedAsTheContract(unittest.TestCase):
    """`reference/oh-my-pi/` is a gitignored copy of the oh-my-pi fork, frozen
    around 0.73. What runs is npm-global `@earendil-works/pi-coding-agent`.

    Reading a type from the fork produced a confident wrong conclusion in one
    session: its `BeforeAgentStartEventResult` has no `systemPrompt`, which made
    correct bridge code look like a defect. Nothing but prose stood in the way of
    the next session doing the same.

    Mentioning the fork is fine — warning about it requires naming it. Citing it
    where an API contract is decided, without naming the package that actually
    ships that contract, is not.
    """

    # Where contract decisions get made. docs/retro and the oh-my-pi-learnings
    # notes are narrative about the fork itself, not decisions taken from it.
    SCOPES = [
        ("pi-extensions", (".ts",)),
        ("scripts", (".py",)),
        ("pi-rules", (".md",)),
        ("docs/superpowers/specs", (".md",)),
        ("docs/superpowers/plans", (".md",)),
    ]
    ROOT_FILES = ["CLAUDE.md"]

    def _files(self):
        for rel, exts in self.SCOPES:
            base = os.path.join(ROOT, *rel.split("/"))
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames if d != "node_modules"]
                for fn in filenames:
                    if fn.endswith(exts):
                        full = os.path.join(dirpath, fn)
                        yield os.path.relpath(full, ROOT).replace("\\", "/")
        for rel in self.ROOT_FILES:
            yield rel

    def test_the_fork_is_never_cited_without_the_package_that_actually_ships(self):
        offenders = []
        for rel in self._files():
            body = read(rel)
            if "reference/oh-my-pi" in body and "earendil-works" not in body:
                offenders.append(rel)
        self.assertEqual(
            offenders, [],
            "these cite the frozen fork copy as if it were the contract; name "
            "@earendil-works/pi-coding-agent, which is what runs",
        )


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
        # calibrate-context needs a running local model AND the pi binary to
        # measure against; there is nothing for CI to check. It writes only the
        # gitignored local override, so it cannot affect a clean checkout.
        documented.discard("scripts/calibrate-context.py")
        # make-probe-fixture builds measurement inputs; it is not a check and has
        # nothing to assert. Sizing by --tokens needs a model server to tokenize
        # against, and its own unit tests (which inject the git reader and the
        # tokenizer) are what CI actually runs.
        documented.discard("scripts/make-probe-fixture.py")
        # measure-advancer launches Pi against the local model, several minutes
        # per run; CI has neither. Unlike the others it carries its own
        # falsifiability check — `--self-check` reproduces counts from a fixture
        # copied out of a captured session and REFUSES to measure when they
        # disagree, which is what CI would otherwise have been asked to do. It
        # earned that check the hard way: the first version's counters were
        # structurally incapable of returning anything but zero, twice.
        documented.discard("scripts/measure-advancer.py")
        # report-task-shapes reports; it asserts nothing. Its input is
        # ~/.pi/agent/sessions, which does not exist on a CI runner, so wiring it
        # in would print "no sessions" and exit 0 on every run — a check
        # structurally incapable of failing, which this repo counts as worse than
        # no check. It has no unit tests either; CI guards only that it compiles.
        documented.discard("scripts/report-task-shapes.py")
        # measure-drift launches Pi against the local model twice per data point
        # and flips a shipped config flag while it runs; CI has neither the model
        # nor any business mutating pi-config. Its scorer — the part that can be
        # wrong in a way that matters — is covered by tests/test_measure_drift.py,
        # which CI does run, and it refuses to start when the installed bridge
        # reads a different config than the one it would flip.
        documented.discard("scripts/measure-drift.py")
        # mine-session reads a session log from ~/.pi and reports; it asserts
        # nothing and there are no sessions on a CI runner, so wiring it in
        # would print a header and exit 0 every time. Its extraction — the
        # part that can be wrong in a way that hides a defect — is covered by
        # tests/test_mine_session.py against a captured fixture, which CI runs.
        documented.discard("scripts/mine-session.py")
        # report-plan-order reads the same place mine-session does. On a CI
        # runner there is no ~/.pi/agent/sessions, so it would print "0 sessions"
        # and exit 0 forever — a check that cannot fail, which this repo counts
        # as worse than no check. Its classifier is covered by
        # tests/test_report_plan_order.py against captured shapes, which CI runs.
        documented.discard("scripts/report-plan-order.py")
        missing = [c for c in sorted(documented) if c not in self.ci]
        self.assertEqual(missing, [], "documented checks absent from CI: %s" % missing)


if __name__ == "__main__":
    unittest.main()
