# Skill 撞名隔離設計 (2026-07-21)

> `restore.py` 目前把 `external/*` submodule skill（如 `agents-best-practices`、`darwin-skill`）的原始路徑直接寫進全域 `~/.pi/agent/settings.json` 的 `skills` 陣列，skill 的 `name:` 用上游原名，未加任何隔離。使用者之後獨立 `pi install` 任何剛好同名的東西，會撞名——Pi「同名保留先找到那個」的規則下，harness 已註冊的那份永遠贏，使用者新裝的永遠被 `(skipped)`。

## 目標 (Goal)
撞名時能自動判斷「真的是同一套東西重複裝」還是「純粹剛好同名、內容不同」，前者去重不留兩份，後者才隔離兩份都留。沒撞名的情況（多數時候）維持現狀，不增加任何額外負擔或 context 成本。

## 非目標 (Non-Goals)
- 不改變 `pi-skills/core/*` 現有的 `managed_skills` 物理複製機制（已經安全，不在此次範圍）。
- 不掃描 `~/.agents/skills/`、專案層級 `.pi/skills/`——目前回報的撞名都發生在 `~/.pi/agent/skills/`，其餘位置沒有證據顯示有問題，先不做（YAGNI）。
- 不處理「同一套東西升級後 hash 變了」的版號漂移問題——已知限制，見下方錯誤處理。

## 架構與元件

### A. `scripts/restore.py` — 新函式 `resolve_external_skill(path)`
在寫入 `profile_skills` 之前，對每一個 `external/*` 來源的 skill path：
1. 讀該路徑下 `SKILL.md` 的 frontmatter `name:` 欄位（用既有的 YAML 解析邏輯，缺欄位/解析失敗 → fail open，照舊直接註冊原路徑，只印一行警告，不中斷 restore）。
2. 檢查 `~/.pi/agent/skills/<name>/SKILL.md` 是否存在。若存在，用**名字**（不是路徑，兩者本來就會落在同一個固定目的地）比對 `managed_skills` 清單：`<name>` 已在清單內 → 視為 harness 自己先前的 staged 產出，不當撞名處理，跳過整個第 3–4 步，直接照第 3 步「不存在」分支走（原路徑寫入）。
3. 不存在 → 沒撞名，行為完全不變：直接把 `external/<name>` 原路徑加進 `profile_skills`（如現在）。
4. 存在 → 撞名，內容比對：
   - 對兩份 `SKILL.md`做正規化（統一換行、去除頭尾空白）後算 hash。
   - **hash 相同**：判定是同一套東西重複裝。跳過註冊 harness 這份（不寫進 `profile_skills`），印一行 info log 說明「偵測到 <name> 與既有全域 skill 內容相同，已跳過重複註冊」。使用者原本裝的那份繼續生效，不多佔 context。
   - **hash 不同**：判定是巧合撞名、不同功能。呼叫 `stage_renamed_skill(src, name)`（見下）產生隔離副本，並印一行 warning 說明兩者都保留、新名字是什麼。

### B. `scripts/restore.py` — 新函式 `stage_renamed_skill(src_dir, original_name)`
- 目的地：`~/.pi/agent/skills/harness-<original_name>/`（物理複製，比照 `pi-skills/core` 現有模式，不是 settings.json 路徑指標）。
- 複製 `src_dir` 全部內容到目的地，複製後就地修改目的地那份 `SKILL.md` 的 frontmatter：`name: harness-<original_name>`（符合 Pi 命名規則：小寫、連字號，見 `docs/skills.md` Name Rules）。**來源 submodule 完全不動**，維持 pristine，`git submodule update` 不會衝突。
- 把 `harness-<original_name>` 加進 `managed_skills` 清單（延伸現有那份 `["hello-reflect", "planning-with-files", ...]` allowlist），讓下次 restore 能安全刪除重裝，不會被誤判成別人的東西。

### C. 冪等性
`restore.py` 重跑多次，第 3 步（撞名檢查）要先排除自己上次跑出來的 `harness-<name>` staged 副本（用 `managed_skills` 清單判斷），否則會把自己先前的輸出當成外部撞名，錯誤觸發二次改名。

## 資料流
```
restore.py 執行
  → 走訪 profile_skills 裡每個 external/* 來源
    → 讀 SKILL.md name:
    → name 存在於 ~/.pi/agent/skills/ 且非 harness 自己管理的？
        否 → 照舊，原路徑寫入 profile_skills
        是 → hash 比對
              相同 → 跳過（log info），不寫入 profile_skills
              不同 → stage_renamed_skill() 產生 harness-<name>
                     → 該 staged 路徑寫入 profile_skills
                     → name 加進 managed_skills
```

## 錯誤處理與已知限制
- `SKILL.md` 解析失敗（缺 `name:` 或 YAML 壞掉）→ fail open，維持原行為，印警告，不中斷。
- **版號漂移**：上游 submodule 更新後，就算功能上還是「同一套東西」，hash 會變，可能被誤判成「不同」而多留一份 `harness-<name>`。這是已知取捨——結果是多一份、不是遺失內容，可接受；不在此次範圍內解決語意版本追蹤。
- 掃描範圍只到 `~/.pi/agent/skills/`；其餘 skill 來源位置不掃。

## 測試
延伸 `tests/test_restore.py`：
- `resolve_external_skill`／`stage_renamed_skill` 抽成純函式（不牽動全域 `~/.pi`，用 `tempfile` 建假的來源/目的地目錄），三個案例：無撞名照舊直通、撞名內容相同跳過、撞名內容不同產生 `harness-<name>` 副本且 frontmatter 正確被改名。
- 冪等性：連跑兩次 `resolve_external_skill`，第二次不應把第一次的 staged 副本誤判成外部撞名。
