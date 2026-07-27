/**
 * Skill Catalog Bridge Extension
 *
 * Pi's formatSkillsForPrompt writes name + description + ABSOLUTE PATH into the
 * system prompt for every registered skill, on every turn. Measured here: 145
 * skills = 55,239 chars (~13,809 tokens/turn, 58% of the whole system prompt).
 * The per-skill fixed overhead (XML tags + absolute path + name) is ~213 chars
 * regardless of how short the description is, so trimming descriptions reclaims
 * almost nothing — measured at 2,378 tokens for a 150-char cap. The only
 * effective lever is to not natively register the long tail.
 *
 * restore.py therefore registers a core set natively (full descriptions, Pi's
 * own discovery path untouched) and writes the rest to
 * pi-config/skill-catalog.json. This bridge injects those as an inline NAME
 * LIST so they stay discoverable.
 *
 * Why an inline list rather than a single "index skill" the model must choose
 * to read: an index skill costs ~95 tokens versus ~840 for the list, but it
 * requires the model to take an action first. This harness's primary target is
 * a weak local model, and the stall this whole audit started from was a weak
 * model failing to take an expected action. Paying 745 tokens to put the names
 * unconditionally in front of it buys down the main risk.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

interface CatalogSkill {
  name: string;
  description?: string;
  path: string;
}

// import.meta.url, not require.resolve: Pi's loader shims `require`, but bare
// node does not for an ESM-declared package — and importing the installed copy
// in node is how this bridge gets behaviourally tested.
const HERE = dirname(fileURLToPath(import.meta.url));

function harnessRoot(): string {
  try {
    const pkg = JSON.parse(readFileSync(join(HERE, "package.json"), "utf-8"));
    if (pkg["pi-harness"]?.root) return pkg["pi-harness"].root;
  } catch {}
  return join(HERE, "../..");
}

export function readCatalog(root: string): CatalogSkill[] {
  const path = join(root, "pi-config", "skill-catalog.json");
  if (!existsSync(path)) return [];
  try {
    const data = JSON.parse(readFileSync(path, "utf-8"));
    const skills = data?.skills;
    if (!Array.isArray(skills)) return [];
    return skills.filter(
      (s): s is CatalogSkill => !!s && typeof s.name === "string" && typeof s.path === "string",
    );
  } catch {
    // Malformed catalog: inject nothing. restore.py has already registered the
    // full set natively in that case (skill_tiers_from_config fails open), so
    // silence here means "no tail to advertise", never "skills lost".
    return [];
  }
}

// The wording is the product of a live trigger test, not a guess. The first
// version said "read <catalog> to get its description and SKILL.md path, then
// read that file". The model did step one — it opened the catalog — and then
// called web_search twice for the skill instead of reading the local `path` it
// had just been handed. stealth-web-bridge's own promptGuidelines ("You CAN
// access the internet: call web_search for any task needing current or external
// information") actively pull that way, so the catalog has to say plainly that
// these skills are local files.
export function buildCatalogBlock(skills: CatalogSkill[], catalogPath: string): string {
  if (skills.length === 0) return "";
  const names = skills.map((s) => s.name).sort().join(", ");
  return (
    `\n\n[Skill Catalog] ${skills.length} more skills are installed locally. Their names are ` +
    `listed below; their descriptions are not expanded here, to keep the context small.\n` +
    `To use one, take exactly two steps:\n` +
    `  1. read ${catalogPath} — a JSON list where every entry has "name", "description" and "path".\n` +
    `  2. read the "path" value of the entry you want. That file is the skill.\n` +
    `These are files already on this machine. Do NOT use web_search to look a skill up, and do ` +
    `not guess its contents from the name.\n${names}`
  );
}

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async (_event, ctx) => {
    const skills = readCatalog(harnessRoot());
    if (skills.length === 0) return;
    ctx.ui.setStatus("skill-catalog", `[Skill Catalog] ${skills.length} skills available on demand`);
  });

  pi.on("before_agent_start", (event, _ctx) => {
    const root = harnessRoot();
    const skills = readCatalog(root);
    if (skills.length === 0) return;
    const block = buildCatalogBlock(skills, join(root, "pi-config", "skill-catalog.json").replace(/\\/g, "/"));
    if (!block) return;
    return { systemPrompt: (event.systemPrompt ?? "") + block };
  });
}
