# Skill 撞名隔離設計 (2026-07-21)

> `restore.py` 目前把 `external/*` submodule skill（agents-best-practices、darwin-skill、superpowers 全系列、ecc、qiushi-skill、evolver…幾乎所有 `ext_root` 來源）的原始路徑直接寫進全域 `~/.pi/agent/settings.json` 的 `skills` 陣列，skill 的 `name:` 一律沿用上游原名，未加任何隔離。使用者之後獨立 `pi install` 任何剛好同名的東西，會撞名——Pi「同名保留先找到那個」的規則下，harness 已註冊的那份永遠贏，使用者新裝的永遠被 `(skipped)`。
>
> **v2 修正（取代原本 restore.py-only 設計）**：原設計只在 `restore.py` 執行的當下判斷一次，之後使用者任何時間點自己 `pi install`，都不會被重新檢查——等於凍結在安裝當下的快照，沒解決「每次裝新的都會衝突」這個實際情境。改成用 Pi 的 `resources_discover` 事件（每次啟動/reload session 都會重新觸發）做**即時**判斷，不是安裝時一次性判斷。

## 目標 (Goal)
撞名時能自動判斷「真的是同一套東西重複裝」還是「純粹剛好同名、內容不同」，前者去重不留兩份，後者才隔離兩份都留。判斷要**每次啟動 pi 都重新檢查**，涵蓋使用者在兩次 harness 更新之間自己裝的任何東西。沒撞名的情況（多數時候）維持現狀，不增加任何額外負擔或 context 成本。

## 非目標 (Non-Goals)
- 不改變 `pi-skills/core/*` 現有的 `managed_skills` 物理複製機制（已經安全，不在此次範圍）。
- 不掃描 `~/.agents/skills/`、專案層級 `.pi/skills/`——目前回報的撞名都發生在 `~/.pi/agent/skills/`，其餘位置沒有證據顯示有問題，先不做（YAGNI）。
- 不處理「同一套東西升級後 hash 變了」的版號漂移問題——已知限制，見下方錯誤處理。

## 架構與元件

### A. `scripts/restore.py` — 職責收斂：只決定「這個 profile 要哪些 external skill」
`profile_skills` 清單依來源拆成兩條路：
- 來源是 `pi_skills_root`（這個 harness 自己authored 的，如 chrome-cdp、dev-browser、graphify）→ **行為不變**，照舊直接寫進 `settings.json` 的 `skills` 陣列。
- 來源是 `ext_root`（`external/*`，所有 submodule skill，範圍是目前 `profile_skills` 裡所有 `os.path.join(ext_root, ...)` 的項目，不只 agents-best-practices/darwin-skill 兩個）→ **不再**直接寫進 `settings.json`。改為寫進新檔案 `pi-config/external-skills-manifest.json`：`[{"name": "<upstream name，若讀不到先留空由 Component B 執行期自己讀>", "path": "<絕對路徑>"}]`。

### B. 新 extension `pi-extensions/skill-namespace-guard/index.ts`
```ts
pi.on("resources_discover", async (event, ctx) => {
  // event.reason: "startup" | "reload" — 兩者都要重新判斷，不快取上次結果
  const manifest = readManifest();  // pi-config/external-skills-manifest.json
  const skillPaths: string[] = [];
  for (const { path: srcDir } of manifest) {
    const name = readSkillName(srcDir);          // 讀 SKILL.md frontmatter name:
    const existing = findGlobalSkill(name);       // 掃 ~/.pi/agent/skills/<name>/SKILL.md
    if (!existing || isHarnessManaged(name)) {
      skillPaths.push(srcDir);                    // 沒撞名，或撞到的是自己先前 staged 的產出：原路徑
      continue;
    }
    if (contentHash(srcDir) === contentHash(existing)) {
      // 同一套東西重複裝：跳過，讓使用者自己那份生效，不重複註冊
      continue;
    }
    skillPaths.push(stageRenamedSkill(srcDir, name)); // 內容不同：產生 harness-<name> 隔離副本
  }
  return { skillPaths };
});
```
- `stageRenamedSkill`：物理複製 `srcDir` 到 `~/.pi/agent/skills/harness-<name>/`，就地把複製後那份 `SKILL.md` 的 `name:` 改成 `harness-<name>`（符合 Pi 命名規則），來源 submodule 完全不動。寫檔前先檢查目的地是否已存在且內容相同（避免每次啟動都重複複製浪費 I/O）。
- `isHarnessManaged(name)`：檢查 `name` 是否以 `harness-` 開頭**且**對應的 staged 副本確實是本次 manifest 算出來該有的內容——用來排除「撞到自己先前的產出」，見下方冪等性。
- 這支邏輯**每次 session 啟動/reload 都重新跑**，不是安裝時判斷一次——這是這次修正的核心，直接對應「使用者隨時自己裝東西」的實際情境。

### C. 新 extension 的裝設方式
`skill-namespace-guard` 比照現有其他 bridge，由 `restore.py` 用標準三處註冊流程裝好（`profile_extensions` 追加、`internal_bridge_names`、刪除迴圈都要有它）——**不是選配**。這支拿掉的話，`external/*` 那批 skill 會整批從 `settings.json` 消失且沒有替代註冊路徑（比撞名更嚴重的 regression），所以必須跟 `yes-hooks-bridge`／`case-bridge` 等核心 bridge 同等級，standard profile 一定裝。

### D. 冪等性
每次 `resources_discover` 觸發，判斷「`~/.pi/agent/skills/<name>/`」是不是自己上次 staged 的產出，不能只看名字有沒有 `harness-` 字首（使用者理論上也可能自己裝一個剛好叫 `harness-xxx` 的東西，機率低但要處理）——改用內容比對：staged 副本的內容應該等於「原始 `external/<name>` 內容 + 只有 `name:` 欄位被改寫」，可重新計算預期內容比對，相符才視為自己的產出、跳過撞名處理；不符（真的又被別的東西佔用同名）才再次觸發改名邏輯。

## 資料流
```
pi 啟動 / /reload
  → resources_discover 觸發（每次都重跑，不快取）
    → 讀 pi-config/external-skills-manifest.json（restore.py 決定的「這個 profile 要哪些 external skill」）
    → 逐一：讀 name: → 查 ~/.pi/agent/skills/<name>/ 是否存在
        不存在 → 原路徑
        存在且是自己先前 staged 的產出（內容比對確認）→ 原路徑
        存在且是別人的東西：
          hash 相同 → 跳過，不重複註冊
          hash 不同 → stageRenamedSkill() → harness-<name> 路徑
    → 回傳 { skillPaths: [...] }
```

## 錯誤處理與已知限制
- `SKILL.md` 解析失敗（缺 `name:` 或格式壞掉）→ fail open，原路徑照樣回傳，`ctx.ui.notify` 印一行警告，不中斷 `resources_discover`（一個壞掉不能拖垮其他所有 skill 的註冊）。
- **版號漂移**：上游 submodule 更新後，就算功能上還是「同一套東西」，hash 會變，可能被誤判成「不同」而多留一份 `harness-<name>`。已知取捨——結果是多一份、不是遺失內容，可接受；不在此次範圍內解決語意版本追蹤。
- 每次啟動都重新掃描/複製 staged 副本：已加「目的地內容相同就跳過複製」的短路，避免每次都重寫磁碟；純掃描+hash 比對本身成本很小（十幾個小檔案），不預期造成明顯啟動延遲。
- 掃描範圍只到 `~/.pi/agent/skills/`；其餘 skill 來源位置不掃。

## 測試
- `readSkillName`／`findGlobalSkill`／`contentHash`／`stageRenamedSkill` 抽成純函式，用 Pi 真正的 jiti loader 載入 `skill-namespace-guard`，餵假的 `resources_discover` event + 用 `tempfile` 建的假 `~/.pi/agent/skills/` 目錄，涵蓋：無撞名直通、撞名內容相同跳過、撞名內容不同產生 `harness-<name>`。
- 冪等性：同一組輸入連續觸發兩次 `resources_discover`，第二次不能把第一次的 staged 副本誤判成外部撞名。
- `restore.py` 那邊：延伸 `tests/test_restore.py`，確認 `external-skills-manifest.json` 有正確寫出所有 `ext_root` 來源（不只兩個範例名字），且這些條目**不再**同時出現在 `settings.json` 的 `skills` 陣列裡（避免雙重註冊）。
- `skill-namespace-guard` 三處註冊：比照 `test_yes_hooks_bridge.py`／`test_stealth_web_bridge.py` 的 `TestRestoreWiring` 寫法。
