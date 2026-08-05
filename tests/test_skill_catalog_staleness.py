"""The catalogue is generated, gitignored, and nobody checked it stayed correct.

restore.py tiers local skills: the names in `harness-config.json` `skillTiers.core`
stay natively registered, and the rest are demoted into
`pi-config/skill-catalog.json` (restore.py `tier_local_skills` / `merge_into_catalog`).
skill-catalog-bridge then tells the model to read that file to find a skill.

Measured on this machine, 2026-08-04, before any change here:

    pi-skills/core     -> 14 skills that should be catalogued
    pi-skills/optional ->  4 skills that should be catalogued
    skill-catalog.json -> 104 entries, all under external/*, 0 from pi-skills

So `hello-reflect`, `thinking-frameworks`, `grilling-protocol`, `camofox-stealth`
and eleven others were registered nowhere and catalogued nowhere — unreachable
by any route, while README.md and docs/core/CORE_CONCEPTS.md describe them as
working features. The tiering code is correct; the generated file was stale and
nothing compared the two.

The catalogue is gitignored, so a check that reads it cannot be a CI gate — that
is the `green on my machine` scar in the other direction, a test that passes
locally and fails on every fresh checkout. Hence: the comparison is a pure
function tested here against fixtures, and validate-config.py applies it to the
real file only when the real file exists.
"""

import importlib.util
import shutil
import tempfile
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate = _load("validate_config", "scripts/validate-config.py")
restore = _load("restore", "scripts/restore.py")


class TestMissingLocalSkillDetection(unittest.TestCase):
    def test_reports_a_local_skill_the_catalog_never_received(self):
        catalog = {"skills": [{"name": "some-external", "path": "external/x/SKILL.md"}]}
        expected = [{"name": "hello-reflect", "path": "pi-skills/core/hello-reflect/SKILL.md"}]
        self.assertEqual(
            validate.missing_from_catalog(catalog, expected), ["hello-reflect"]
        )

    def test_reports_nothing_when_every_demoted_skill_is_present(self):
        catalog = {"skills": [
            {"name": "hello-reflect", "path": "pi-skills/core/hello-reflect/SKILL.md"},
            {"name": "some-external", "path": "external/x/SKILL.md"},
        ]}
        expected = [{"name": "hello-reflect", "path": "pi-skills/core/hello-reflect/SKILL.md"}]
        self.assertEqual(validate.missing_from_catalog(catalog, expected), [])

    def test_a_name_registered_by_an_external_skill_still_counts_as_present(self):
        """merge_into_catalog documents that an existing entry wins: the external
        tiering already resolved that name. Flagging it would be a false alarm."""
        catalog = {"skills": [{"name": "planning-with-files", "path": "external/pwf/SKILL.md"}]}
        expected = [{"name": "planning-with-files", "path": "pi-skills/core/planning-with-files/SKILL.md"}]
        self.assertEqual(validate.missing_from_catalog(catalog, expected), [])

    def test_a_malformed_catalog_is_reported_rather_than_swallowed(self):
        """An unreadable catalogue makes the bridge inject nothing at all, which
        is a worse outcome than a stale one and must not read as 'fine'."""
        expected = [{"name": "hello-reflect", "path": "p/SKILL.md"}]
        self.assertEqual(validate.missing_from_catalog({}, expected), ["hello-reflect"])
        self.assertEqual(validate.missing_from_catalog(None, expected), ["hello-reflect"])


class TestExpectedLocalTail(unittest.TestCase):
    def test_the_expected_tail_comes_from_the_same_code_restore_uses(self):
        """Recomputing the rule by hand is how the two lists drift apart in the
        first place, so this asks restore.py rather than reimplementing it."""
        mode, core = restore.skill_tiers_from_config(
            os.path.join(ROOT, "pi-config", "harness-config.json"))
        self.assertEqual(mode, "tiered")
        _kept, tail = restore.tier_local_skills(
            os.path.join(ROOT, "pi-skills", "core"), set(core))
        names = [t["name"] for t in tail]
        self.assertIn("hello-reflect", names)
        self.assertNotIn(
            "planning-with-files", names,
            "the local copy is shadowed on purpose by the submodule's "
            "pi-planning-with-files and is never installed — cataloguing it "
            "would advertise the same capability twice, pointing at the copy "
            "that was deliberately left unregistered")

    def test_directories_without_a_skill_md_are_not_skills(self):
        """pi-skills/core/bridges holds RATIONALE decision docs."""
        mode, core = restore.skill_tiers_from_config(
            os.path.join(ROOT, "pi-config", "harness-config.json"))
        _kept, tail = restore.tier_local_skills(
            os.path.join(ROOT, "pi-skills", "core"), set(core))
        self.assertNotIn("bridges", [t["name"] for t in tail])


class TestMergeVerifiesItsOwnWrite(unittest.TestCase):
    """The staleness check below only runs where a catalogue already exists.

    That is correct for a gitignored artefact, but it leaves the moment the
    artefact is produced unguarded: `restore.py` demoted 18 local skills into the
    catalogue and none of them arrived, and the run reported success. A write that
    does not check itself is how a generated file drifts from the rule that
    generates it in the first place.

    `merge_into_catalog` reports what it failed to persist. This is a write
    verification, not a second copy of the policy — which skills get demoted stays
    in `tier_local_skills`, the one place that decides it.
    """

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="catalog-write-")
        self.addCleanup(lambda: shutil.rmtree(self.base, ignore_errors=True))
        self.path = os.path.join(self.base, "skill-catalog.json")

    def test_reports_nothing_when_every_entry_landed(self):
        entries = [{"name": "hello-reflect", "path": "pi-skills/core/hello-reflect/SKILL.md"}]
        self.assertEqual(restore.merge_into_catalog(self.path, entries), [])
        written = json.load(open(self.path, encoding="utf-8"))["skills"]
        self.assertIn("hello-reflect", [s["name"] for s in written])

    def test_an_entry_already_present_counts_as_landed(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "skills": [
                {"name": "planning-with-files", "path": "external/pwf/SKILL.md"}]}, f)
        entries = [{"name": "planning-with-files", "path": "pi-skills/core/pwf/SKILL.md"}]
        self.assertEqual(restore.merge_into_catalog(self.path, entries), [])

    def test_reports_the_entries_when_the_write_could_not_happen(self):
        """A directory where the catalogue should be is the shape this hits on a
        broken install; the run must say so rather than report success."""
        blocked = os.path.join(self.base, "as-a-dir.json")
        os.makedirs(blocked)
        entries = [{"name": "hello-reflect", "path": "p/SKILL.md"}]
        self.assertEqual(restore.merge_into_catalog(blocked, entries), ["hello-reflect"])

    def test_merging_nothing_is_not_a_failure(self):
        self.assertEqual(restore.merge_into_catalog(self.path, []), [])


class TestTheRealCatalogWhenItExists(unittest.TestCase):
    """Runs against the generated file, and skips where there isn't one.

    pi-config/skill-catalog.json is gitignored (.gitignore:10). A fresh checkout
    has no catalogue to be stale, and asserting on one that is not there is how a
    test goes green locally and red for everyone else.
    """

    def test_every_demoted_local_skill_is_reachable(self):
        catalog_path = os.path.join(ROOT, "pi-config", "skill-catalog.json")
        if not os.path.exists(catalog_path):
            self.skipTest("skill-catalog.json is generated by restore.py; none here")

        with open(catalog_path, encoding="utf-8") as f:
            catalog = json.load(f)

        _mode, core = restore.skill_tiers_from_config(
            os.path.join(ROOT, "pi-config", "harness-config.json"))
        expected = []
        for sub in ("core", "optional"):
            _kept, tail = restore.tier_local_skills(
                os.path.join(ROOT, "pi-skills", sub), set(core))
            expected.extend(tail)

        missing = validate.missing_from_catalog(catalog, expected)
        self.assertEqual(
            missing, [],
            "local skills demoted from native registration but absent from the "
            "catalogue are reachable by no route at all; re-run "
            "`python scripts/setup.py --mode restore`",
        )


if __name__ == "__main__":
    unittest.main()
