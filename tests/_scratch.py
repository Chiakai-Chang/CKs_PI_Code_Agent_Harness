"""Per-process scratch paths for the node drivers the tests write out.

Every one of these files used to be a fixed name under `tests/` —
`.tmp_repeat_driver.mjs`, `.tmp_bashc_driver.mjs`, and thirty-odd more. One
process at a time, that is fine. Two at a time, they delete each other's files
in `finally` and the failures land on whichever test happened to be running:
measured 2026-08-12, two concurrent `python -m unittest tests.test_universal_tool_parser`
gave `failures=25, errors=5` and `failures=42, errors=9` — none of them real,
and none of them naming the actual cause.

That happens more than it sounds like it would: a suite that overruns a timeout
gets backgrounded and keeps running, and the next suite starts on top of it.
The symptom is a red run that goes green on a retry, which is the worst kind of
signal this repo can produce — it trains you to dismiss reds.

The files stay under `tests/` on purpose. Several drivers are read back through
guards that measure a path against the project root, so moving them to the
system temp directory would change what is being tested.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scratch(name: str) -> str:
    """`.tmp_foo.mjs` -> `<repo>/tests/.tmp_foo.<pid>.mjs`.

    The pid goes before the extension, not after: node decides how to parse a
    file from its `.mjs` suffix, and `.mjs.1234` is not `.mjs`.
    """
    base, ext = os.path.splitext(name)
    return os.path.join(ROOT, "tests", "%s.%d%s" % (base, os.getpid(), ext))


def scratch_rel(name: str) -> str:
    """The same file as a repo-relative path, for tests that hand the path to a
    guard as an argument rather than opening it."""
    return "tests/" + os.path.basename(scratch(name))
