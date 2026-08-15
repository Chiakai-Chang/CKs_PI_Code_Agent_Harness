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
import { readFileSync, existsSync, mkdirSync, cpSync, writeFileSync, rmSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { homedir } from "node:os";
import { createHash } from "node:crypto";

interface ManifestEntry {
  path: string;
}

// Conflict report written to pi-config/skill-conflict-report.json for human
// auditability. The runtime collision handling (staged renamed copies) runs
// silently; the report is the artifact that survives across sessions.
interface ConflictReport {
  version: number;
  generatedAt: string;
  sources: {
    harnessSkills: { name: string; path: string }[];
    externalSkills: { name: string | null; path: string; sourceSubmodule: string }[];
  };
  conflicts: {
    name: string;
    paths: { path: string; source: "harness" | "external" }[];
    resolution: "staged-renamed-copy" | "identical-content-skipped" | "no-action-yet";
  }[];
}

function harnessRoot(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  try {
    const pkg = JSON.parse(readFileSync(join(here, "package.json"), "utf-8"));
    if (pkg["pi-harness"]?.root) return pkg["pi-harness"].root;
  } catch {}
  return join(here, "../..");
}

/**
 * Put PI_HARNESS_ROOT where the model's shell can actually see it.
 *
 * `restore.py:944` writes `settings.env.PI_HARNESS_ROOT` into
 * ~/.pi/agent/settings.json, and `pi-rules/AGENTS.md:21` tells the reader "the
 * PI_HARNESS_ROOT env var is injected by scripts/restore.py". Neither is true:
 * Pi's `Settings` interface (installed `core/settings-manager.d.ts`, lines
 * 66-116) has no `env` field, nothing in the runtime reads one, and the block is
 * a zombie config of exactly the kind this repo forbids.
 *
 * The cost is not theoretical. Measured on session 01a004bc (2026-08-15), a
 * `/case` run in an unrelated project: the command's own text says to run
 * `$PI_HARNESS_ROOT/external/Local-Agent-Workspace/scripts/bootstrap.py` and to
 * read `$PI_HARNESS_ROOT/.../SKILL.md`. The model echoed the variable, got `[]`,
 * and went hunting for the harness by guessing absolute paths — 41 of its 224
 * calls (18%) ended up inside this repo instead of the user's project. Across
 * all 53 real sessions in other projects the same pattern accounts for 218 of
 * 2832 calls (7%). Ten instruction files depend on this variable.
 *
 * Why this works where the settings block does not: the bash tool builds its
 * environment per call from `getShellEnv()`, which spreads `process.env`
 * (installed `utils/shell.js:103`, called from `resolveSpawnContext` in
 * `core/tools/bash.js:119`). Extensions run inside that same process, so an
 * assignment here reaches every shell the model opens afterwards.
 *
 * Set at registration rather than in `session_start`, so no ordering between
 * handlers can leave a command running before it. Never overwrites an operator's
 * own value: someone who exported it deliberately outranks us.
 */
function exportHarnessRoot(): void {
  if (process.env.PI_HARNESS_ROOT) return;
  // Validated, not just non-empty. `package.json` ships `"root":
  // "TODO_SET_BY_RESTORE"` and restore.py patches it on install, so an
  // unpatched copy would otherwise export the placeholder — and a wrong path is
  // worse than an empty one, because the model will act on it. Caught by
  // test_it_points_at_a_real_harness_checkout on the repo copy.
  //
  // Leaving it unset when nothing checks out is the honest failure: AGENTS.md
  // tells the model that an empty value means stop and say so, not go hunting.
  for (const candidate of [harnessRoot(), join(dirname(fileURLToPath(import.meta.url)), "../..")]) {
    if (!candidate) continue;
    try {
      if (!existsSync(join(candidate, "pi-extensions"))) continue;
      if (!existsSync(join(candidate, "pi-skills"))) continue;
    } catch {
      continue;
    }
    process.env.PI_HARNESS_ROOT = candidate.replace(/\\/g, "/");
    return;
  }
}

function readManifest(ctx?: { ui?: { notify?: (msg: string, level: string) => void } }): ManifestEntry[] {
  const manifestPath = join(harnessRoot(), "pi-config", "external-skills-manifest.json");
  if (!existsSync(manifestPath)) return [];
  try {
    return JSON.parse(readFileSync(manifestPath, "utf-8"));
  } catch (err) {
    // A parse failure here silently drops every external/* skill from this
    // session with zero signal — the manifest is machine-generated by
    // restore.py so this should be rare, but "rare and silent" is exactly
    // the kind of failure that goes unnoticed for a long time. Surface it.
    const msg = err instanceof Error ? err.message : String(err);
    ctx?.ui?.notify?.(
      `[skill-namespace-guard] Could not parse ${manifestPath} (${msg}) — all external/* skills are unavailable this session. Re-run restore.py to regenerate it.`,
      "warning",
    );
    return [];
  }
}

// Scans pi-skills/ for harness-authored skills (non-recursive SKILL.md lookup).
function scanHarnessSkills(): { name: string; path: string }[] {
  const skillsDir = join(harnessRoot(), "pi-skills");
  if (!existsSync(skillsDir)) return [];
  const results: { name: string; path: string }[] = [];
  let entries: string[];
  try {
    entries = readdirSync(skillsDir);
  } catch {
    return results;
  }
  for (const entry of entries) {
    const skillMd = join(skillsDir, entry, "SKILL.md");
    if (!existsSync(skillMd)) continue;
    // Non-recursive: top-level pi-skills/<entry>/SKILL.md only. Nested
    // sub-skills (optional/camofox-stealth/SKILL.md) are reported by their
    // directory name, not the group parent.
    const name = readFrontmatterName(skillMd);
    results.push({ name: name ?? entry, path: join(skillsDir, entry) });
    // Also scan one level deeper (e.g. pi-skills/optional/<sub>/SKILL.md)
    let subDir = join(skillsDir, entry);
    let subEntries: string[];
    try {
      subEntries = readdirSync(subDir).filter((n) => statSync(join(subDir, n)).isDirectory());
    } catch {
      continue;
    }
    for (const sub of subEntries) {
      const subSkillMd = join(subDir, sub, "SKILL.md");
      if (existsSync(subSkillMd)) {
        results.push({ name: readFrontmatterName(subSkillMd) ?? sub, path: join(subDir, sub) });
      }
    }
  }
  return results;
}

// Extracts the frontmatter `name:` field. SKILL.md format per docs/skills.md:
// "---\nname: my-skill\ndescription: ...\n---". Returns null if unparseable
// (fail open — caller registers the raw path unchanged rather than dropping
// the skill).
export function readFrontmatterName(skillMdPath: string): string | null {
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
  if (!nameMatch) return null;
  return unquote(nameMatch[1].trim());
}

/**
 * Strip one layer of matching quotes from a frontmatter value.
 *
 * `external/yes.md/skills/yes/SKILL.md` declares `name: "yes"`, and the quotes
 * are not decoration: unquoted, YAML 1.1 reads `yes` as the boolean true, so
 * upstream had to quote it. Reading the value with a regex and not undoing that
 * gave this guard the literal name `"yes"`, which fails its own safety pattern —
 * measured 2026-08-11 in a real session, where every start printed
 *
 *     Skipping unsafe skill name ""yes"" ... registering as-is
 *
 * A warning that fires every session for a correct file is noise, and noise is
 * what stops warnings being read.
 */
export function unquote(value: string): string {
  // The backreference is the point: only a value quoted on BOTH sides with
  // the same character is unwrapped. Without it `"yes` would lose its opening
  // quote and nothing would be left to say the file is malformed.
  const m = value.match(/^(["'])([\s\S]*)\1$/);
  return m ? m[2] : value;
}

// Some manifest entries (e.g. external/taste-skill/skills, external/yes.md/
// skills) point at a CONTAINER directory holding multiple sub-skills, each
// with its own SKILL.md one level down — not a single skill with SKILL.md
// directly inside. Pi's own recursive discovery already handles this
// correctly. There is no meaningful single "name" to collision-check at the
// container level, so this is a normal, expected shape, not an anomaly —
// detect it so the caller can register the raw path silently instead of
// warning on every session start forever.
function isSkillContainer(dirPath: string): boolean {
  let entries: string[];
  try {
    entries = readdirSync(dirPath);
  } catch {
    return false;
  }
  return entries.some((name) => {
    try {
      return statSync(join(dirPath, name, "SKILL.md")).isFile();
    } catch {
      return false;
    }
  });
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
  // .trim() intentionally widens beyond CRLF->LF normalization: two skills
  // differing only by leading/trailing whitespace (e.g. a trailing blank
  // line) are still treated as identical for dedup purposes. Deliberate,
  // not an oversight — do not remove to match the spec literally.
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

  // cpSync is an overlay, not a mirror — it never removes files that were
  // deleted from srcDir since the last stage. Clear destDir first so the
  // copy below is a true mirror of the current source contents.
  rmSync(destDir, { recursive: true, force: true });
  mkdirSync(destDir, { recursive: true });
  cpSync(srcDir, destDir, { recursive: true });
  writeFileSync(destSkillMd, expected, "utf-8");
  return destDir;
}

// Detects cross-source name collisions between harness skills (pi-skills/) and
// external submodule skills, writing a persistent report for auditability.
// The runtime collision handling (staged renamed copies) still runs inline;
// this report is the durable artifact that survives across sessions.
function buildConflictReport(
  harnessSkills: { name: string; path: string }[],
  manifest: ManifestEntry[],
): ConflictReport {
  const externalSkills: { name: string | null; path: string; sourceSubmodule: string }[] = [];
  for (const entry of manifest) {
    const srcSkillMd = join(entry.path, "SKILL.md");
    if (existsSync(srcSkillMd)) {
      externalSkills.push({
        name: readFrontmatterName(srcSkillMd),
        path: entry.path,
        sourceSubmodule: entry.path.split("/").find((_, i, arr) => arr[i] === "external") ? entry.path.split("/")[1] : entry.path,
      });
    }
  }

  // Build name->paths map across all sources; report names appearing in >1 source.
  const nameMap = new Map<string, { path: string; source: "harness" | "external" }[]>();
  for (const hs of harnessSkills) {
    nameMap.set(hs.name, [...(nameMap.get(hs.name) ?? []), { path: hs.path, source: "harness" }]);
  }
  for (const es of externalSkills) {
    if (es.name) {
      nameMap.set(es.name, [...(nameMap.get(es.name) ?? []), { path: es.path, source: "external" }]);
    }
  }

  const conflicts: ConflictReport["conflicts"] = [];
  for (const [name, paths] of nameMap) {
    if (paths.length < 2) continue;
    // Determine resolution status from runtime state:
    // - staged renamed copy exists at ~/.pi/agent/skills/harness-<name> → resolved
    // - identical content across sources → skipped intentionally
    // - otherwise no action yet
    const stagedDir = join(homedir(), ".pi", "agent", "skills", `harness-${name}`);
    let resolution: ConflictReport["conflicts"][number]["resolution"] = "no-action-yet";
    if (existsSync(join(stagedDir, "SKILL.md"))) {
      resolution = "staged-renamed-copy";
    } else {
      // Check identical content across all SKILL.md files
      const hashes = new Set<string>();
      for (const p of paths) {
        try {
          hashes.add(normalizedHash(readFileSync(join(p.path, "SKILL.md"), "utf-8")));
        } catch {}
      }
      if (hashes.size === 1) resolution = "identical-content-skipped";
    }
    conflicts.push({ name, paths, resolution });
  }

  return { version: 1, generatedAt: new Date().toISOString(), sources: { harnessSkills, externalSkills }, conflicts };
}

function writeConflictReport(report: ConflictReport) {
  const reportPath = join(harnessRoot(), "pi-config", "skill-conflict-report.json");
  try {
    mkdirSync(dirname(reportPath), { recursive: true });
    writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n", "utf-8");
  } catch (err) {
    // Report writing failure is non-fatal; the runtime handling still works.
    const msg = err instanceof Error ? err.message : String(err);
    // Can't ctx.ui.notify here (no context); the report simply won't be written.
  }
}

export default function (pi: ExtensionAPI) {
  // First statement in the extension, before any handler is registered: ten
  // instruction files tell the model to run `$PI_HARNESS_ROOT/...` in bash, and
  // until 2026-08-16 that variable was empty in every shell it opened.
  exportHarnessRoot();

  pi.on("resources_discover", async (_event, ctx) => {
    const manifest = readManifest(ctx);
    const skillPaths: string[] = [];

    // Build and write the cross-source conflict report first (before runtime
    // collision resolution runs), so it captures the pre-resolution state.
    const harnessSkills = scanHarnessSkills();
    writeConflictReport(buildConflictReport(harnessSkills, manifest));

    for (const entry of manifest) {
      try {
        const srcDir = entry.path;
        const srcSkillMd = join(srcDir, "SKILL.md");
        const name = readFrontmatterName(srcSkillMd);

        if (!name) {
          if (!isSkillContainer(srcDir)) {
            ctx.ui.notify(`[skill-namespace-guard] Could not read name: from ${srcSkillMd}; registering as-is.`, "warning");
          }
          skillPaths.push(srcDir);
          continue;
        }

        // Defense-in-depth: `name` is interpolated into filesystem paths
        // below (stageRenamedSkill's destDir, existingSkillMd). A value
        // like "../../evil" would let join() normalize outside
        // ~/.pi/agent/skills/. Reject anything that isn't a safe path
        // segment and fail open exactly like the missing-name case.
        if (!/^[A-Za-z0-9._-]+$/.test(name)) {
          ctx.ui.notify(
            `[skill-namespace-guard] Skipping unsafe skill name "${name}" from ${srcSkillMd} (must match [A-Za-z0-9._-]+); registering as-is.`,
            "warning",
          );
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
