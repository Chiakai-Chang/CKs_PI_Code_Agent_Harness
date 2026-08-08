"""Terminating the launcher is not terminating the run.

2026-08-09, and the owner spotted it before any check did: the model was still
busy while nothing appeared to be running here. Two orphaned `pi --print`
processes from runs this script had "terminated" the night before were alive,
holding slots on the local model server, and therefore competing with every
measurement taken afterwards. Two of those runs reported "quiet for 180s" — a
number produced by contention with orphans they had created themselves.

`pi` resolves to `pi.CMD` on Windows, so the launch goes through a shell and
`Popen.terminate()` reaches the cmd.exe wrapper only. This repo already carried
the same shape from async-exec: on Windows spawn() hands back the launcher, so
what must be asserted is killability, not pid equality.
"""

import importlib.util
import os
import subprocess
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "measure_advancer", os.path.join(ROOT, "scripts", "measure-advancer.py"))
ma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ma)


def children_of(pid):
    """Direct children, via CIM. `wmic` is gone from this machine entirely —
    which is also how the first version of the orphan check in the script under
    test could only ever return an empty list."""
    script = ("Get-CimInstance Win32_Process -Filter 'ParentProcessId=%d' | "
              "ForEach-Object { $_.ProcessId }" % pid)
    out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                         capture_output=True, text=True, errors="replace").stdout
    return [int(t) for t in out.split() if t.isdigit()]


def alive(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid],
                         capture_output=True, text=True).stdout
    return str(pid) in out


@unittest.skipUnless(os.name == "nt", "the launcher/child split is a Windows problem")
class TestTheChildDiesToo(unittest.TestCase):
    def test_a_shell_launched_child_does_not_survive(self):
        """A shell that outlives its parent is exactly the shape that leaked.

        The sleeper lives in a temp file rather than an inline -c string:
        quoting a python one-liner through cmd through Popen(shell=True) is
        four layers deep, and it produced an unterminated string literal on the
        first attempt — the ninth escaping casualty of this stretch."""
        import tempfile
        fd, sleeper = tempfile.mkstemp(suffix=".py")
        os.close(fd)
        with open(sleeper, "w", encoding="utf-8") as f:
            f.write("import time" + chr(10) + "time.sleep(120)" + chr(10))
        self.addCleanup(lambda: os.path.exists(sleeper) and os.remove(sleeper))

        proc = subprocess.Popen("cmd /c %s %s" % (sys.executable, sleeper),
                                shell=True)
        self.addCleanup(ma.stop_tree, proc)
        time.sleep(3)
        child_pids = children_of(proc.pid)
        self.assertTrue(child_pids, "no child spawned; the case has no teeth")

        ma.stop_tree(proc)
        deadline = time.time() + 25
        while time.time() < deadline and any(alive(p) for p in child_pids):
            time.sleep(0.5)
        survivors = [p for p in child_pids if alive(p)]
        self.assertEqual(survivors, [],
                         "children survived the stop, which is how two runs "
                         "kept generating against the model server all night")

    def test_stop_tree_is_safe_on_an_already_dead_process(self):
        proc = subprocess.Popen([sys.executable, "-c", "pass"])
        proc.wait(timeout=30)
        ma.stop_tree(proc)   # must not raise


class TestTheRunnerRefusesContendedMeasurements(unittest.TestCase):
    def test_orphan_pids_is_consulted_before_measuring(self):
        with open(os.path.join(ROOT, "scripts", "measure-advancer.py"),
                  encoding="utf-8") as f:
            body = f.read().split("def main(", 1)[1]
        self.assertIn("orphan_pids()", body,
                      "a measurement taken beside an unknown second consumer "
                      "of the same server is not a measurement")
        self.assertIn("return 2", body.split("orphan_pids()", 1)[1][:400])

class TestTheTimeoutsComeFromMeasuredGaps(unittest.TestCase):
    """The quiet default was 180s while a completing run's p95 gap was 190s and
    its max was 237s, so it could only ever cut runs short — and the two "0
    claims" results it produced were the instrument answering, not the model.

    A timeout picked by feel is this repo's oldest recurring mistake in a new
    costume: it measures the observer's patience."""

    def test_quiet_is_above_the_observed_maximum_gap(self):
        import argparse, io, contextlib
        src = open(os.path.join(ROOT, "scripts", "measure-advancer.py"),
                   encoding="utf-8").read()
        self.assertRegex(src, r'"--quiet".*default=(600|[7-9]\d\d|\d{4,})',
                         "quiet must clear the 237s max gap measured on a run "
                         "that actually completed a claim")

    def test_the_limit_clears_the_only_run_that_got_anywhere(self):
        src = open(os.path.join(ROOT, "scripts", "measure-advancer.py"),
                   encoding="utf-8").read()
        self.assertRegex(src, r'"--limit".*default=(2400|[3-9]\d{3}|\d{5,})')



if __name__ == "__main__":
    unittest.main()
