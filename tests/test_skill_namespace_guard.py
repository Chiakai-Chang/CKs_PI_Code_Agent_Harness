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

    def test_package_is_esm_with_harness_root(self):
        pkg = read(self.PKG)
        self.assertIn('"type": "module"', pkg)
        self.assertIn("pi-harness", pkg)


if __name__ == "__main__":
    unittest.main()
