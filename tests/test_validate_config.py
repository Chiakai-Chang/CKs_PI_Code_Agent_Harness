"""Tests for scripts/validate-config.py, the documented health check.

The script had never been exercised by a test, and both of its states were
wrong in opposite directions:

  * On a CLEAN CLONE (the state a new user runs it in) it FAILED: only
    pi-config/settings.json.example is tracked, and it legitimately lacks
    defaultModel/defaultProvider — setup.py writes those after probing the
    local LLM server.
  * On a DEVELOPER MACHINE it FAILED on the "no committed machine paths" rule,
    which it evaluated against pi-config/settings.json — a gitignored file that
    is never committed and is *supposed* to hold the injected shell path. The
    check could not detect the thing it existed to prevent, while failing on
    the normal post-setup state.

Same shape as the scar in CLAUDE.md: a check pointed at the gitignored artifact
instead of the tracked one.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "validate-config.py")


def make_repo(settings=None, example=None):
    """Build a throwaway repo root with just the files the checker reads."""
    tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp, ".git"))
    cfg = os.path.join(tmp, "pi-config")
    os.makedirs(cfg)
    if example is not None:
        with open(os.path.join(cfg, "settings.json.example"), "w", encoding="utf-8") as f:
            json.dump(example, f)
    if settings is not None:
        with open(os.path.join(cfg, "settings.json"), "w", encoding="utf-8") as f:
            json.dump(settings, f)
    return tmp


def run_validator(repo):
    proc = subprocess.run(
        [sys.executable, SCRIPT, "--root", repo],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    return proc.returncode, proc.stdout + proc.stderr


TRACKED_TEMPLATE = {
    "packages": [], "skills": [], "extensions": [], "prompts": [],
    "lastChangelogVersion": "0.73.0",
}
LOCAL_SETTINGS = {
    "defaultModel": "some-model", "defaultProvider": "local-server",
    "apiBase": "http://127.0.0.1:8080",
    "shellPath": "C:\\Program Files\\Git\\bin\\bash.exe",
}


class TestValidateConfig(unittest.TestCase):
    def tearDown(self):
        for d in getattr(self, "_dirs", []):
            shutil.rmtree(d, ignore_errors=True)

    def _repo(self, **kw):
        d = make_repo(**kw)
        self._dirs = getattr(self, "_dirs", []) + [d]
        return d

    def test_clean_clone_passes(self):
        """Only the template exists — the state every new user starts from."""
        code, out = run_validator(self._repo(example=TRACKED_TEMPLATE))
        self.assertEqual(code, 0, out)
        self.assertIn("0 failure", out)

    def test_local_machine_path_is_expected_not_a_failure(self):
        """setup.py injects the real shell path into the gitignored copy."""
        code, out = run_validator(self._repo(settings=LOCAL_SETTINGS, example=TRACKED_TEMPLATE))
        self.assertEqual(code, 0, out)
        self.assertIn("0 failure", out)

    def test_machine_path_in_tracked_template_fails(self):
        """This is the violation the rule actually exists to catch."""
        bad = dict(TRACKED_TEMPLATE, shellPath="C:\\Program Files\\Git\\bin\\bash.exe")
        code, out = run_validator(self._repo(example=bad))
        self.assertNotEqual(code, 0, out)
        self.assertIn("settings.json.example contains a machine-specific path", out)

    def test_machine_path_in_template_caught_even_when_local_settings_exist(self):
        """A developer machine must not mask a bad committed template."""
        bad = dict(TRACKED_TEMPLATE, shellPath="/usr/local/bin/bash")
        code, out = run_validator(self._repo(settings=LOCAL_SETTINGS, example=bad))
        self.assertNotEqual(code, 0, out)
        self.assertIn("settings.json.example contains a machine-specific path", out)

    def test_local_settings_still_require_model_keys(self):
        """The relaxation applies only to the template, not to a real config."""
        code, out = run_validator(self._repo(settings={"apiBase": "http://x"}, example=TRACKED_TEMPLATE))
        self.assertNotEqual(code, 0, out)
        self.assertIn("defaultModel", out)

    def test_repo_as_shipped_passes(self):
        """The real repo, in whatever state this machine is in."""
        code, out = run_validator(ROOT)
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
