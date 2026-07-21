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
