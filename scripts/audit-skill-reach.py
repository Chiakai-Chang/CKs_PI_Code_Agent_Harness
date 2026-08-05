#!/usr/bin/env python3
"""Write down which skills the model can actually find, and which it cannot.

Pi renders two tiers into the system prompt. Core skills get name, description
and location; catalogued ones get a bare name and a pointer to a JSON file. A
description is what lets a request find a skill by vocabulary, so the tier a
skill lands in decides whether it is reachable at all.

That split was invisible until 2026-08-06, when a dump of the real prompt showed
`case-framework` — the harness owner's own task-queue protocol, carrying every
mechanism a design round had just converged on rebuilding — sitting in the
nameless 122 alongside the whole of the README's Layer 1.

This script writes the full picture to a file so the next session does not have
to rediscover it. Run it after any change to `skillTiers`, to the catalog, or to
what is installed under the neighbouring `~/.agents/skills/`.

    python scripts/audit-skill-reach.py --out docs/measurements/skill-reachability.md

The truest input is a dumped prompt, because it shows what Pi actually sent
rather than what the config intends:

    PI_HARNESS_DUMP_PROMPT=/tmp/p.txt pi --print "hi"
    python scripts/audit-skill-reach.py --prompt /tmp/p.txt --out <file>

Without `--prompt` the core tier is read from
`pi-config/external-skills-manifest.json`, which omits skills registered outside
this harness — and those turned out to be 19 of the 43.
"""

import argparse
import io
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_text(path):
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def frontmatter(skill_md):
    """Return (name, description) from a SKILL.md, or ("", "").

    Parsed rather than regexed off the whole file: a description that mentions
    `---` inside its text would otherwise swallow the rest of the document.
    """
    text = read_text(skill_md)
    if not text.startswith("---"):
        return "", ""
    end = text.find("\n---", 3)
    if end < 0:
        return "", ""
    block = text[3:end]
    out = {}
    key = None
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            key = m.group(1).lower()
            out[key] = m.group(2).strip()
        elif key and line.startswith((" ", "\t")):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out.get("name", ""), out.get("description", "")


def source_of(path):
    """Where a skill comes from, which is what decides who can re-tier it."""
    p = path.replace("\\", "/")
    root = ROOT.replace("\\", "/")
    if p.startswith(root + "/external/ecc/"):
        return "ECC 子模組"
    if p.startswith(root + "/external/"):
        rest = p[len(root) + len("/external/"):]
        return "external/" + rest.split("/")[0]
    if p.startswith(root + "/pi-skills/"):
        return "本 harness pi-skills/"
    if "/.agents/skills/" in p:
        return "~/.agents/skills/(外來)"
    if "/.pi/agent/skills/" in p:
        return "~/.pi/agent/skills/(自動探索)"
    return "其他"


def core_from_prompt(path):
    """The skills Pi really advertised, read out of a dumped system prompt."""
    text = read_text(path)
    block = re.search(r"<available_skills>(.*?)</available_skills>", text, re.S)
    if not block:
        return None
    out = []
    for m in re.finditer(
        r"<skill>\s*<name>([^<]*)</name>\s*<description>(.*?)</description>\s*"
        r"<location>([^<]*)</location>",
        block.group(1),
        re.S,
    ):
        out.append({
            "name": m.group(1).strip(),
            "description": " ".join(m.group(2).split()),
            "path": m.group(3).strip(),
        })
    return out


def core_from_manifest():
    """Fallback: what the harness intends to register.

    Incomplete by construction — it knows nothing about skills installed by a
    neighbouring tool, and those occupied 19 of the 43 slots when this was
    written.
    """
    path = os.path.join(ROOT, "pi-config", "external-skills-manifest.json")
    try:
        entries = json.loads(read_text(path))
    except ValueError:
        return []
    out = []
    for e in entries:
        d = e["path"] if isinstance(e, dict) else e
        md = os.path.join(d, "SKILL.md")
        name, desc = frontmatter(md)
        out.append({"name": name or os.path.basename(d), "description": desc, "path": md})
    return out


def catalog_entries():
    path = os.path.join(ROOT, "pi-config", "skill-catalog.json")
    try:
        data = json.loads(read_text(path))
    except ValueError:
        return []
    return data.get("skills", data) if isinstance(data, dict) else data


def escape_cell(s, limit=200):
    s = " ".join((s or "").split())
    if len(s) > limit:
        s = s[: limit - 1] + "…"
    return s.replace("|", "\\|")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", help="a file written by PI_HARNESS_DUMP_PROMPT")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    core = core_from_prompt(args.prompt) if args.prompt else None
    core_source = "實測 prompt(%s)" % args.prompt if core else \
                  "external-skills-manifest.json(不含外來技能)"
    if core is None:
        core = core_from_manifest()

    cat = []
    for e in catalog_entries():
        name, desc = frontmatter(e["path"])
        cat.append({
            "name": e["name"],
            "description": desc,
            "path": e["path"],
            "declared_name": name,
        })
    cat.sort(key=lambda x: x["name"])

    by_source = {}
    for c in cat:
        by_source.setdefault(source_of(c["path"]), []).append(c)

    core_names = {c["name"] for c in core}
    lines = []
    w = lines.append

    w("# 技能可達性全掃")
    w("")
    w("由 `scripts/audit-skill-reach.py` 產生於 %s。**不要手改** —— 重跑即可更新。"
      % time.strftime("%Y-%m-%d %H:%M"))
    w("")
    w("core 層來源:%s" % core_source)
    w("")
    w("## 為什麼要有這份文件")
    w("")
    w("Pi 把技能分兩層寫進 system prompt:core 層有 name + description + location,")
    w("catalog 層只有名字加一個 JSON 檔路徑。**描述是請求靠詞彙找到技能的唯一途徑**,")
    w("所以一個技能落在哪一層,決定它到底能不能被用到。")
    w("")
    w("2026-08-06 dump 實際 prompt 才發現:`case-framework`(擁有者自己寫的任務佇列協定,")
    w("內含一整輪設計會議剛收斂要重造的每一個機制)就躺在沒有描述的那 122 個裡,")
    w("README 畫的 Layer 1 三個技能也全部在裡面。")
    w("")
    w("## 總計")
    w("")
    w("| 層 | 數量 | 模型看得到什麼 |")
    w("|---|---:|---|")
    w("| core | %d | 名稱、描述、絕對路徑 —— 可靠詞彙發現 |" % len(core))
    w("| catalog | %d | 只有名稱 —— 需先讀 catalog JSON 再讀 SKILL.md |" % len(cat))
    w("")

    w("## core 層(有描述,%d)" % len(core))
    w("")
    w("| 技能 | 來源 | 描述 |")
    w("|---|---|---|")
    for c in sorted(core, key=lambda x: (source_of(x["path"]), x["name"])):
        w("| `%s` | %s | %s |" % (c["name"], source_of(c["path"]),
                                  escape_cell(c["description"], 160)))
    w("")

    foreign = [c for c in core if source_of(c["path"]).startswith("~/.agents")]
    if foreign:
        w("### 其中不屬於本 harness 的(%d)" % len(foreign))
        w("")
        w("由鄰居工具安裝在 `~/.agents/skills/`。**本 harness 的 tiering 降不了它們** ——")
        w("降級只作用在自己註冊的技能上。它們佔著描述層,與 harness 自己的技能搶同一類請求。")
        w("")
        for c in sorted(foreign, key=lambda x: x["name"]):
            w("- `%s`" % c["name"])
        w("")

    w("## catalog 層(只有名字,%d)" % len(cat))
    w("")
    w("描述欄是從各自的 `SKILL.md` frontmatter 讀出來的 —— **模型在 prompt 裡看不到這一欄**。")
    w("列在這裡是為了讓人看得出哪些能力其實存在。")
    w("")
    for src in sorted(by_source, key=lambda s: (-len(by_source[s]), s)):
        items = by_source[src]
        w("### %s(%d)" % (src, len(items)))
        w("")
        w("| 技能 | 描述(模型看不到) |")
        w("|---|---|")
        for c in items:
            flag = " ⚠️同名也在 core" if c["name"] in core_names else ""
            w("| `%s`%s | %s |" % (c["name"], flag, escape_cell(c["description"])))
        w("")

    w("## 重新產生")
    w("")
    w("```bash")
    w("PI_HARNESS_DUMP_PROMPT=/tmp/p.txt pi --print \"hi\"")
    w("python scripts/audit-skill-reach.py --prompt /tmp/p.txt --out %s" % args.out)
    w("```")
    w("")
    w("沒有 `--prompt` 時 core 層從 `external-skills-manifest.json` 讀,")
    w("**那份清單不含外來技能**,寫這份文件時它漏掉了 43 個裡的 19 個。")

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print("core %d / catalog %d -> %s" % (len(core), len(cat), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
