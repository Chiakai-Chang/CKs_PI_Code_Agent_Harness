import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestSkillNamespaceGuardContract(unittest.TestCase):
    IDX = "pi-extensions/skill-namespace-guard/index.ts"
    PKG = "pi-extensions/skill-namespace-guard/package.json"

    def test_hooks_resources_discover(self):
        c = read(self.IDX)
        self.assertIn('pi.on("resources_discover"', c)

    def test_reads_manifest(self):
        c = read(self.IDX)
        self.assertIn("external-skills-manifest.json", c)

    def test_reads_frontmatter_name(self):
        c = read(self.IDX)
        self.assertIn("function readFrontmatterName", c)

    def test_hashes_normalized_content(self):
        c = read(self.IDX)
        self.assertIn("function normalizedHash", c)
        self.assertIn('replace(/\\r\\n/g, "\\n")', c)

    def test_stages_renamed_copy_on_collision(self):
        c = read(self.IDX)
        self.assertIn("function stageRenamedSkill", c)
        self.assertIn("harness-${name}", c)

    def test_skips_duplicate_on_identical_content(self):
        c = read(self.IDX)
        self.assertIn("continue", c)  # identical-hash branch skips registration

    def test_fails_open_on_missing_name(self):
        c = read(self.IDX)
        self.assertIn("Could not read name:", c)

    def test_container_directories_silent_no_warning(self):
        """Some manifest entries (external/taste-skill/skills, external/
        yes.md/skills, external/qiushi-skill/skills, external/loopy/skills)
        are container directories with multiple sub-skills one level down,
        no SKILL.md at the container level itself. Pi's own recursive
        discovery already handles this. Regression guard for a real
        live-session finding: these produced a permanent, unnecessary
        "Could not read name:" warning on every single pi startup before
        this fix — real functionality was never broken (fail-open still
        registered the raw path correctly), but the noise was new and
        avoidable."""
        c = read(self.IDX)
        self.assertIn("function isSkillContainer", c)
        idx_check = c.index("if (!name) {")
        idx_end = c.index("continue;", idx_check)
        block = c[idx_check:idx_end]
        self.assertIn("isSkillContainer(srcDir)", block)

    def test_malformed_manifest_notifies_instead_of_silent_drop(self):
        """Final whole-branch review (2026-07-21) flagged this as a real Minor
        never actually fixed in that review's fix wave: readManifest()
        returned [] on any JSON.parse failure with zero user-facing signal —
        every external/* skill would silently vanish from a session with no
        way to notice why. Guard: the catch path must call ctx.ui.notify."""
        c = read(self.IDX)
        idx_fn = c.index("function readManifest")
        idx_end = c.index("\n}", idx_fn)
        block = c[idx_fn:idx_end]
        self.assertIn("catch (err)", block)
        self.assertIn("ctx?.ui?.notify?.(", block)

    def test_package_is_esm_with_harness_root(self):
        pkg = read(self.PKG)
        self.assertIn('"type": "module"', pkg)
        self.assertIn("pi-harness", pkg)


if __name__ == "__main__":
    unittest.main()


def _node_major():
    import re, shutil, subprocess
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


def run_guard(script):
    import json, os, subprocess
    driver = os.path.join(ROOT, "tests", ".tmp_nsguard_driver.mjs")
    url = "file:///" + os.path.join(
        ROOT, "pi-extensions", "skill-namespace-guard", "index.ts").replace("\\", "/")
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
class TestAQuotedNameIsNotAnUnsafeName(unittest.TestCase):
    """Measured 2026-08-11 in a real session, on every single start:

        Warning: [skill-namespace-guard] Skipping unsafe skill name ""yes""
        from ...\external\yes.md\skills\yes\SKILL.md
        (must match [A-Za-z0-9._-]+); registering as-is.

    The file is correct. `name: "yes"` is quoted because YAML 1.1 reads a bare
    `yes` as the boolean true, so upstream had no choice. The guard read the
    value with a regex and kept the quotes, then failed its own safety pattern
    against them. A warning that fires every session for a correct file is
    noise, and noise is what stops warnings being read."""

    import json as _json

    def unquote(self, value):
        import json
        return run_guard("process.stdout.write(JSON.stringify(m.unquote(%s)));"
                         % json.dumps(value))

    def name_of(self, rel):
        import json, os
        return run_guard("process.stdout.write(JSON.stringify("
                         "m.readFrontmatterName(%s)));"
                         % json.dumps(os.path.join(ROOT, rel).replace("\\", "/")))

    def test_the_real_file_that_warned_reads_as_yes(self):
        self.assertEqual(
            self.name_of("external/yes.md/skills/yes/SKILL.md"), "yes")

    def test_an_unquoted_name_is_untouched(self):
        self.assertEqual(
            self.name_of("external/superpowers/skills/brainstorming/SKILL.md"),
            "brainstorming")

    def test_both_quote_characters_are_handled(self):
        self.assertEqual(self.unquote('"yes"'), "yes")
        self.assertEqual(self.unquote("'yes'"), "yes")

    def test_an_unpaired_quote_is_left_alone(self):
        """Stripping one side would hide a malformed file instead of surfacing
        it — the name would look safe and the frontmatter would still be wrong."""
        for value in ['"yes', 'yes"', "'yes", "\"yes'"]:
            with self.subTest(value=value):
                self.assertEqual(self.unquote(value), value)

    def test_quotes_inside_a_name_are_not_stripped(self):
        self.assertEqual(self.unquote('ye"s'), 'ye"s')
