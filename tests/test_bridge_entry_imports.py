"""A bridge is only installed if the modules its entry point imports came too.

verify-bridges.py checked that a bridge's entry file exists and that a
package.json sits beside it. It never looked at what the entry imports. Six of
the twelve bridges import sibling modules — `./advisory.ts`, `./research.js`,
`./truncate.js` and so on — and if one of those were missing from the installed
copy, verification would report twelve healthy bridges while Pi failed to load
the extension at session start.

That is not hypothetical shape: `restore.py` copies bridge directories wholesale
today, but nothing states that it must, and this repo has already shipped a
bridge whose real behaviour diverged from what the checks measured.

Specifier resolution follows what the bridges actually do. Two styles are in use
— `./x.ts` (async-exec-bridge, ecc-hooks-bridge) and `./x.js`
(deep-research-bridge, stealth-web-bridge) — and the `.js` ones name files that
are `.ts` on disk, so a `.js` specifier is satisfied by either extension.
"""

import importlib.util
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

spec = importlib.util.spec_from_file_location(
    "verify_bridges", os.path.join(ROOT, "scripts", "verify-bridges.py"))
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def write(path, body=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


class TestMissingSiblingModules(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="entry-imports-")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.base, ignore_errors=True))
        self.entry = os.path.join(self.base, "index.ts")

    def test_reports_a_sibling_that_was_never_copied(self):
        write(self.entry, 'import { X } from "./advisory.ts";\n')
        self.assertEqual(verify.missing_local_imports(self.entry), ["./advisory.ts"])

    def test_says_nothing_when_the_sibling_is_there(self):
        write(self.entry, 'import { X } from "./advisory.ts";\n')
        write(os.path.join(self.base, "advisory.ts"), "export const X = 1;\n")
        self.assertEqual(verify.missing_local_imports(self.entry), [])

    def test_a_js_specifier_is_satisfied_by_a_ts_file(self):
        """deep-research-bridge imports `./research.js`; the file on disk is
        `research.ts`. Both styles ship in this repo and both work under Pi."""
        write(self.entry, 'import { parse } from "./research.js";\n')
        write(os.path.join(self.base, "research.ts"), "export const parse = 1;\n")
        self.assertEqual(verify.missing_local_imports(self.entry), [])

    def test_package_imports_are_not_local_files(self):
        write(self.entry,
              'import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";\n'
              'import { join } from "node:path";\n')
        self.assertEqual(verify.missing_local_imports(self.entry), [])

    def test_resolves_a_relative_path_into_a_subdirectory(self):
        write(self.entry, 'import { helper } from "./lib/helper.ts";\n')
        write(os.path.join(self.base, "lib", "helper.ts"), "export const helper = 1;\n")
        self.assertEqual(verify.missing_local_imports(self.entry), [])

    def test_reports_every_missing_specifier_not_only_the_first(self):
        write(self.entry,
              'import { a } from "./a.ts";\n'
              'import { b } from "./b.ts";\n')
        self.assertEqual(verify.missing_local_imports(self.entry), ["./a.ts", "./b.ts"])

    def test_dynamic_import_of_a_sibling_counts_too(self):
        """`await import("./x.ts")` fails just as hard at runtime."""
        write(self.entry, 'const m = await import("./late.ts");\n')
        self.assertEqual(verify.missing_local_imports(self.entry), ["./late.ts"])

    def test_an_unreadable_entry_is_not_reported_as_missing_imports(self):
        """The entry-exists check owns that failure; reporting it twice buries
        the real one."""
        self.assertEqual(verify.missing_local_imports(os.path.join(self.base, "nope.ts")), [])


class TestTheRealBridgesResolve(unittest.TestCase):
    def test_every_shipped_bridge_entry_finds_its_siblings(self):
        base = os.path.join(ROOT, "pi-extensions")
        offenders = {}
        for name in sorted(os.listdir(base)):
            entry = os.path.join(base, name, "index.ts")
            if not os.path.isfile(entry):
                continue
            missing = verify.missing_local_imports(entry)
            if missing:
                offenders[name] = missing
        self.assertEqual(offenders, {})


if __name__ == "__main__":
    unittest.main()
