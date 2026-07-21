/**
 * Skill Namespace Guard Extension
 *
 * external/* submodule skills carry generic upstream names (agents-best-
 * practices, darwin-skill, superpowers's brainstorming, ...). restore.py no
 * longer registers them directly in settings.json — it writes their paths to
 * pi-config/external-skills-manifest.json instead, and this extension
 * resolves them live on every resources_discover (session start/reload):
 *
 *   - No existing global skill with that name → register the raw path.
 *   - Existing global skill, identical content → skip (don't duplicate;
 *     the user's own independent install already covers it).
 *   - Existing global skill, different content → stage an isolated copy at
 *     ~/.pi/agent/skills/harness-<name>/ with a patched name: frontmatter,
 *     leave the user's original untouched, register the staged copy.
 *
 * This re-runs every session, unlike a restore-time-only check, so it keeps
 * catching collisions introduced by anything the user installs independently
 * between harness updates.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync, existsSync, mkdirSync, cpSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { homedir } from "node:os";
import { createHash } from "node:crypto";

interface ManifestEntry {
  path: string;
}

function harnessRoot(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  try {
    const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf-8"));
    if (pkg["pi-harness"]?.root) return pkg["pi-harness"].root;
  } catch {}
  return join(here, "../..");
}

function readManifest(): ManifestEntry[] {
  const manifestPath = join(harnessRoot(), "pi-config", "external-skills-manifest.json");
  if (!existsSync(manifestPath)) return [];
  try {
    return JSON.parse(readFileSync(manifestPath, "utf-8"));
  } catch {
    return [];
  }
}

// Extracts the frontmatter `name:` field. SKILL.md format per docs/skills.md:
// "---\nname: my-skill\ndescription: ...\n---". Returns null if unparseable
// (fail open — caller registers the raw path unchanged rather than dropping
// the skill).
function readFrontmatterName(skillMdPath: string): string | null {
  if (!existsSync(skillMdPath)) return null;
  let raw: string;
  try {
    raw = readFileSync(skillMdPath, "utf-8");
  } catch {
    return null;
  }
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;
  const nameMatch = match[1].match(/^name:\s*(.+?)\s*$/m);
  return nameMatch ? nameMatch[1].trim() : null;
}

// Rewrites only the frontmatter block's name: field, leaving the rest of the
// file (body, other frontmatter fields) untouched. If no name: field exists
// in the frontmatter, prepends one.
function patchSkillName(rawContent: string, newName: string): string {
  const match = rawContent.match(/^(---\r?\n)([\s\S]*?)(\r?\n---)([\s\S]*)$/);
  if (!match) return rawContent;
  const [, open, frontmatter, close, rest] = match;
  const patched = /^name:\s*.+$/m.test(frontmatter)
    ? frontmatter.replace(/^name:\s*.+$/m, `name: ${newName}`)
    : `name: ${newName}\n${frontmatter}`;
  return `${open}${patched}${close}${rest}`;
}

function normalizedHash(content: string): string {
  const normalized = content.replace(/\r\n/g, "\n").trim();
  return createHash("sha256").update(normalized, "utf-8").digest("hex");
}

// Stages an isolated, renamed copy at ~/.pi/agent/skills/harness-<name>/.
// Always mirrors the current source directory in full (cpSync) and then
// (re)writes the patched SKILL.md — no "skip if already staged" shortcut.
// A content-only check on SKILL.md alone can't detect changes to sibling
// files (scripts/, references/, ...), which would otherwise go stale
// forever. This runs once per Pi session start on small skill directories,
// so unconditional re-copy is cheap; correctness wins over the I/O saving.
function stageRenamedSkill(srcDir: string, name: string, srcRaw: string): string {
  const destDir = join(homedir(), ".pi", "agent", "skills", `harness-${name}`);
  const destSkillMd = join(destDir, "SKILL.md");
  const expected = patchSkillName(srcRaw, `harness-${name}`);

  mkdirSync(destDir, { recursive: true });
  cpSync(srcDir, destDir, { recursive: true });
  writeFileSync(destSkillMd, expected, "utf-8");
  return destDir;
}

export default function (pi: ExtensionAPI) {
  pi.on("resources_discover", async (_event, ctx) => {
    const manifest = readManifest();
    const skillPaths: string[] = [];

    for (const entry of manifest) {
      try {
        const srcDir = entry.path;
        const srcSkillMd = join(srcDir, "SKILL.md");
        const name = readFrontmatterName(srcSkillMd);

        if (!name) {
          ctx.ui.notify(`[skill-namespace-guard] Could not read name: from ${srcSkillMd}; registering as-is.`, "warning");
          skillPaths.push(srcDir);
          continue;
        }

        const existingSkillMd = join(homedir(), ".pi", "agent", "skills", name, "SKILL.md");
        if (!existsSync(existingSkillMd)) {
          skillPaths.push(srcDir);
          continue;
        }

        const srcRaw = readFileSync(srcSkillMd, "utf-8");
        const existingRaw = readFileSync(existingSkillMd, "utf-8");

        if (normalizedHash(existingRaw) === normalizedHash(srcRaw)) {
          // Same skill, already installed independently — don't duplicate.
          continue;
        }

        const stagedDir = stageRenamedSkill(srcDir, name, srcRaw);
        skillPaths.push(stagedDir);
        ctx.ui.notify(
          `[skill-namespace-guard] "${name}" collides with an existing global skill of different content — registered isolated copy as "harness-${name}".`,
          "warning",
        );
      } catch (err) {
        // Fail open per-entry: one broken skill entry (missing path, file
        // deleted mid-run, permission error, ...) must not abort the whole
        // resources_discover call and take every other skill down with it.
        const msg = err instanceof Error ? err.message : String(err);
        ctx.ui.notify(`[skill-namespace-guard] Skipping manifest entry "${entry?.path}" due to error: ${msg}`, "warning");
        continue;
      }
    }

    return { skillPaths };
  });
}
