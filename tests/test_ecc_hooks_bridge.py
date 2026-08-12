"""ecc-hooks-bridge: advisories the model can actually read.

The bridge spent its whole life talking to the terminal. `ctx.ui.notify` paints
the TUI and nothing else; the model never saw a word of it. Verified against the
installed runtime rather than the frozen fork in `reference/oh-my-pi` (0.73-era,
which is missing fields 0.83.0 has):

    @earendil-works/pi-coding-agent@0.83.0
      dist/core/extensions/types.d.ts:778
        interface ToolCallEventResult { block?; reason?; }   <- no other exit
      dist/core/extensions/types.d.ts:790
        interface ToolResultEventResult { content?; details?; isError?; usage?; }
      node_modules/@earendil-works/pi-agent-core/dist/types.d.ts:310
        interface AgentToolResult<T> {
          content: ...   // "Text or image content returned to the model."
          details: T;    // "Arbitrary structured details for logs or UI rendering."
        }

So `content` is the only channel to the model from a hook, and `details` — which
planning-with-files-bridge was returning its progress.md reminder through — is
not one at all.

    dist/core/extensions/types.d.ts:876
        on(event: "turn_end", handler: ExtensionHandler<TurnEndEvent>): void;

`turn_end` declares no result type, so a turn-end finding (stop:format-typecheck)
cannot be handed over where it is produced. It has to wait in a queue for the
next event that does have a channel. That is what advisory.ts exists for.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "tests"))
from _scratch import scratch  # per-process temp names; see tests/_scratch.py

ADVISORY = os.path.join(ROOT, "pi-extensions", "ecc-hooks-bridge", "advisory.ts")


def _node_major():
    if not shutil.which("node"):
        return 0
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return 0
    m = re.match(r"v(\d+)", out.strip())
    return int(m.group(1)) if m else 0


NODE_OK = _node_major() >= 22


def run_js(script):
    driver = scratch(".tmp_ecc_driver.mjs")
    url = "file:///" + ADVISORY.replace("\\", "/")
    with open(driver, "w", encoding="utf-8") as f:
        f.write("import * as m from %s;\n%s" % (json.dumps(url), script))
    try:
        p = subprocess.run(["node", driver], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
        if p.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        if os.path.exists(driver):
            os.remove(driver)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestAdvisoryQueueDelivery(unittest.TestCase):
    def test_a_pushed_advisory_comes_back_out_of_drain(self):
        out = run_js("""
        const q = new m.AdvisoryQueue();
        q.push("plan", "no task_plan.md for this commit");
        process.stdout.write(JSON.stringify({ block: q.drain() }));
        """)
        self.assertIn("no task_plan.md for this commit", out["block"])

    def test_draining_twice_does_not_repeat_the_advisory(self):
        """A queue that keeps re-emitting turns one finding into every-turn noise."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        q.push("plan", "first");
        const a = q.drain();
        const b = q.drain();
        process.stdout.write(JSON.stringify({ a, b }));
        """)
        self.assertIn("first", out["a"])
        self.assertIsNone(out["b"])

    def test_an_empty_queue_drains_to_null_not_an_empty_block(self):
        """Callers append the drain result to tool output; an empty string would
        still cost a content block on every single tool call."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        process.stdout.write(JSON.stringify({ block: q.drain() }));
        """)
        self.assertIsNone(out["block"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestAdvisoryPolicies(unittest.TestCase):
    def test_once_fires_a_key_a_single_time_per_session(self):
        """The plan reminder is a session-level fact. Repeating it every commit
        is how a hint becomes wallpaper."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        const first = q.push("plan", "advice", "once");
        q.drain();
        const second = q.push("plan", "advice", "once");
        process.stdout.write(JSON.stringify({ first, second, block: q.drain() }));
        """)
        self.assertTrue(out["first"])
        self.assertFalse(out["second"])
        self.assertIsNone(out["block"])

    def test_always_lets_the_same_key_fire_again(self):
        """quality-gate findings describe the edit that just happened, so the
        second edit's findings are new information, not a repeat."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        q.push("quality", "first finding", "always");
        const a = q.drain();
        q.push("quality", "second finding", "always");
        const b = q.drain();
        process.stdout.write(JSON.stringify({ a, b }));
        """)
        self.assertIn("first finding", out["a"])
        self.assertIn("second finding", out["b"])

    def test_cooldown_suppresses_a_key_until_n_drains_have_passed(self):
        out = run_js("""
        const q = new m.AdvisoryQueue();
        const results = [];
        results.push(q.push("compact", "x", { cooldown: 2 }));
        q.drain();
        results.push(q.push("compact", "x", { cooldown: 2 }));
        q.drain();
        results.push(q.push("compact", "x", { cooldown: 2 }));
        q.drain();
        results.push(q.push("compact", "x", { cooldown: 2 }));
        process.stdout.write(JSON.stringify({ results }));
        """)
        self.assertEqual(out["results"], [True, False, False, True])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestAdvisoryQueueLifecycle(unittest.TestCase):
    """The queue lives in the extension's default export, which Pi invokes once
    per process, while `session_start` fires once per session. After `/new` the
    same queue is still there, so a `once` advisory would never fire again for
    the rest of the process unless the session boundary clears it."""

    def test_reset_lets_a_once_advisory_fire_for_the_next_session(self):
        out = run_js("""
        const q = new m.AdvisoryQueue();
        q.push("plan", "advice", "once");
        q.drain();
        const beforeReset = q.push("plan", "advice", "once");
        q.reset();
        const afterReset = q.push("plan", "advice", "once");
        process.stdout.write(JSON.stringify({ beforeReset, afterReset }));
        """)
        self.assertFalse(out["beforeReset"])
        self.assertTrue(out["afterReset"])

    def test_reset_drops_advisories_the_previous_session_never_collected(self):
        """A finding about the old session's edits is noise in the new one."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        q.push("stale", "from the previous session", "always");
        q.reset();
        process.stdout.write(JSON.stringify({ pending: q.pendingCount, block: q.drain() }));
        """)
        self.assertEqual(out["pending"], 0)
        self.assertIsNone(out["block"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestAdvisoryKillSwitch(unittest.TestCase):
    """Advisories now enter the model's context, and this harness is tuned for a
    weak local model. A 42,999-char tool result was observed derailing that exact
    model (docs/retro/2026-07-28-web-capability-and-prompt-conflicts.md), which is
    why two other bridges truncate. The drain budget is far below that, but if the
    model does get pulled off course the operator needs to switch this off without
    editing source and reinstalling.

    Fails open, matching `planningBridgeEnabled()` in planning-with-files-bridge:
    an unreadable config must not silently disable a guard.
    """

    def _with_config(self, body):
        base = tempfile.mkdtemp(prefix="advisory-cfg-")
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        if body is not None:
            os.makedirs(os.path.join(base, "pi-config"))
            with open(os.path.join(base, "pi-config", "harness-config.json"), "w",
                      encoding="utf-8") as f:
                f.write(body)
        out = run_js('process.stdout.write(JSON.stringify({ v: m.hookAdvisoriesEnabled(%s) }));'
                     % json.dumps(base.replace("\\", "/")))
        return out["v"]

    def test_off_when_the_operator_turns_it_off(self):
        self.assertFalse(self._with_config('{"enableHookAdvisories": false}'))

    def test_on_when_explicitly_enabled(self):
        self.assertTrue(self._with_config('{"enableHookAdvisories": true}'))

    def test_on_when_the_key_is_absent(self):
        self.assertTrue(self._with_config('{"promptProfile": "auto"}'))

    def test_on_when_there_is_no_config_at_all(self):
        self.assertTrue(self._with_config(None))

    def test_on_when_the_config_is_malformed(self):
        """A broken config must not quietly remove a guard."""
        self.assertTrue(self._with_config("{ not json at all"))

    def test_a_disabled_queue_accepts_nothing_and_hands_over_nothing(self):
        """One decision covers all eight producers; gating each call site would
        be eight chances to miss one."""
        out = run_js("""
        const q = new m.AdvisoryQueue({ enabled: false });
        const pushed = q.push("plan", "advice", "always");
        process.stdout.write(JSON.stringify({ pushed, block: q.drain(), pending: q.pendingCount }));
        """)
        self.assertFalse(out["pushed"])
        self.assertIsNone(out["block"])
        self.assertEqual(out["pending"], 0)

    def test_a_queue_with_no_options_is_enabled(self):
        out = run_js("""
        const q = new m.AdvisoryQueue();
        process.stdout.write(JSON.stringify({ pushed: q.push("k", "v") }));
        """)
        self.assertTrue(out["pushed"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestAdvisoryBudget(unittest.TestCase):
    def test_drain_stops_at_the_char_budget_and_keeps_the_rest_pending(self):
        """Injected on every tool result, an unbounded queue is a context leak."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        q.push("a", "A".repeat(400), "always");
        q.push("b", "B".repeat(400), "always");
        const first = q.drain(500);
        const second = q.drain(500);
        process.stdout.write(JSON.stringify({
          firstLen: first.length, hasA: first.includes("AAAA"), hasB: first.includes("BBBB"),
          secondHasB: second !== null && second.includes("BBBB"),
        }));
        """)
        self.assertLessEqual(out["firstLen"], 500)
        self.assertTrue(out["hasA"])
        self.assertFalse(out["hasB"])
        self.assertTrue(out["secondHasB"])

    def test_a_block_that_is_exactly_the_budget_is_not_truncated(self):
        """The boundary, and a mutation survivor before this test existed:
        `block.length <= budget` and `< budget` differ on exactly this input, and
        the `<` version truncates a message that fits — replacing its last
        characters with the truncation mark for nothing."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        q.push("a", "A".repeat(50), "always");
        const probe = q.drain(100000);          // whole block, un-truncated
        const q2 = new m.AdvisoryQueue();
        q2.push("a", "A".repeat(50), "always");
        const exact = q2.drain(probe.length);   // budget == block length
        process.stdout.write(JSON.stringify({ probe, exact }));
        """)
        self.assertEqual(out["exact"], out["probe"],
                         "a block that exactly fits was truncated")

    def test_a_budget_smaller_than_the_truncation_mark_still_returns_something(self):
        """`Math.max(0, budget - MARK.length)` with `1` instead of `0` differs
        only when the budget is smaller than the mark itself. Slicing with a
        negative length silently counts from the end of the string, so getting
        this wrong returns the TAIL of an advisory — text that reads like a
        complete message and is not."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        q.push("big", "Z".repeat(500), "always");
        const block = q.drain(1);
        process.stdout.write(JSON.stringify({ block }));
        """)
        self.assertIsNotNone(out["block"])
        self.assertNotIn("ZZZ", out["block"],
                         "a 1-char budget returned advisory text, not just the mark")
        # Exactly the mark, with nothing in front of it. `Math.max(1, …)` keeps
        # one character of the header, which reads as the start of a real message.
        self.assertEqual(out["block"], " …[truncated]")

    def test_the_newline_between_advisories_is_counted(self):
        """`next.text.length + 1` — the +1 is the newline that will join them.
        Counting 2 shifts the packing boundary by one character per advisory, so
        a pair that exactly fills the budget would be split across two drains.
        Sized to the boundary here, because anywhere else the margin hides it."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        const header = m.ADVISORY_HEADER.length;
        const a = "A".repeat(20), b = "B".repeat(20);
        // header + (a + newline) + (b + newline) is what drain() accounts for.
        const budget = header + a.length + 1 + b.length + 1;
        q.push("a", a, "always");
        q.push("b", b, "always");
        const first = q.drain(budget);
        process.stdout.write(JSON.stringify({
          hasA: first.includes("AAA"), hasB: first.includes("BBB"),
          pendingAfter: q.pendingCount,
        }));
        """)
        self.assertTrue(out["hasA"])
        self.assertTrue(out["hasB"], "the second advisory was dropped: the "
                                     "per-item cost is over-counted")
        self.assertEqual(out["pendingAfter"], 0)

    def test_an_empty_advisory_is_refused(self):
        """`if (!body) return false;` flipped to `true` queues a blank advisory,
        and drain then emits a header with nothing under it. Empty is ordinary:
        a hook that found nothing to say arrives here with an empty string."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        process.stdout.write(JSON.stringify({
          empty: q.push("a", "", "always"),
          blank: q.push("b", "   ", "always"),
          pending: q.pendingCount,
        }));
        """)
        self.assertFalse(out["empty"])
        self.assertFalse(out["blank"])
        self.assertEqual(out["pending"], 0)

    def test_a_single_oversized_advisory_is_truncated_rather_than_dropped(self):
        """Dropping it silently is how a guard fires zero times and nobody notices."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        q.push("big", "Z".repeat(5000), "always");
        const block = q.drain(300);
        process.stdout.write(JSON.stringify({ len: block === null ? -1 : block.length,
                                              hasZ: block !== null && block.includes("ZZZ") }));
        """)
        self.assertNotEqual(out["len"], -1)
        self.assertLessEqual(out["len"], 300)
        self.assertTrue(out["hasZ"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestAdvisoryBlockShape(unittest.TestCase):
    def test_the_block_is_labelled_so_the_model_can_tell_it_from_tool_output(self):
        """It is appended to a tool result. Unlabelled, it reads as something the
        command printed, and the model has been observed acting on that."""
        out = run_js("""
        const q = new m.AdvisoryQueue();
        q.push("plan", "advice text");
        process.stdout.write(JSON.stringify({ block: q.drain() }));
        """)
        self.assertIn("[ecc-hooks]", out["block"])

    def test_advisoryResult_is_shaped_like_a_ToolResultEventResult(self):
        """The first wiring returned the bare content array from the handler and
        Pi ignored it: the drain ran, the block was built, and the tool result in
        the session log was still just the command's stdout. Unit tests passed
        throughout — only the live run caught it. `ToolResultEventResult` is an
        object with a `content` field, so the helper has to produce that object
        rather than the array it wraps."""
        out = run_js("""
        const content = [{ type: "text", text: "original stdout" }];
        const result = m.advisoryResult(content, "the advice");
        process.stdout.write(JSON.stringify({ result, keys: Object.keys(result) }));
        """)
        self.assertEqual(out["keys"], ["content"])
        texts = [c["text"] for c in out["result"]["content"]]
        self.assertEqual(texts[0], "original stdout")
        self.assertIn("the advice", texts[-1])
        self.assertEqual(out["result"]["content"][-1]["type"], "text")

    def test_advisoryResult_returns_null_when_there_is_nothing_to_say(self):
        """Returning a rebuilt content array for every tool call rewrites results
        that had no reason to change."""
        out = run_js("""
        const content = [{ type: "text", text: "original" }];
        process.stdout.write(JSON.stringify({ result: m.advisoryResult(content, null) }));
        """)
        self.assertIsNone(out["result"])


if __name__ == "__main__":
    unittest.main()
