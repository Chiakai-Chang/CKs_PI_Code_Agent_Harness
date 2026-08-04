# ECC hook 轉譯層 Implementation Plan（2026-08-04）

設計見 [`../specs/2026-08-04-ecc-hook-translation-design.md`](../specs/2026-08-04-ecc-hook-translation-design.md)。

一句話:`ecc-hooks-bridge` 用錯欄位名、少一層外殼、讀錯輸出通道,十五個 ECC hook 只有 `block-no-verify` 在運作。修轉譯,不改 submodule。

## Global Constraints

* **不寫入 `external/ecc`**。它是 submodule,`yes-hooks-bridge` 也會擋。ECC 的契約當作既定外部介面。
* **TDD**。每個新函式先有紅測試。每個守衛**刻意弄壞一次**確認會紅再信綠。
* **改完 bridge 必須 `python scripts/setup.py --mode restore`** 才算測到新版(Pi 跑安裝副本)。
* **送達要在 session JSONL 找到字串**才算數,單元綠不算。
* 數字一律下筆當下實跑。

## File Structure

```
pi-extensions/ecc-hooks-bridge/
  ecc-payload.ts          新增 — 入向/出向轉譯,純函式
  index.ts                改   — 所有呼叫點改走轉譯
  advisory.ts             不動
pi-skills/core/hello-reflect/scripts/
  reflect_core.py         改   — 同時支援 Pi 與 Claude Code 的 session 格式
pi-config/harness-config.json  改 — 新增 enableEccGateGuard（預設 false）
tests/
  test_ecc_payload.py     新增 — 轉譯純函式
  test_ecc_hook_contract.py 新增 — 對真實 ECC hook 的整合測試
  test_hello_reflect.py   新增 — session 解析
```

---

### Task 1 · `ecc-payload.ts` 入向轉譯

`toHookInput(toolName, input, output?)`。

測試（先紅）:
* `bash` `{command}` → `{tool_name:"bash", tool_input:{command}}`,**有外殼**
* `write` `{path, content}` → `tool_input.file_path === path`,且 `content` 保留
* `edit` `{path, edits}` → `tool_input.file_path === path`,`edits` 原樣
* `path` 同時保留在 `tool_input.path`（上游若改用它就不會再斷一次）
* 帶 `output` 時併入 `tool_output`
* 未知工具名 → 仍產出外殼,不丟例外
* `input` 為 null/undefined → 不丟例外

實作後跑 `node` driver 確認,並用真實 ECC hook 驗證(Task 5)。

### Task 2 · `ecc-payload.ts` 出向轉譯

`parseHookOutput({stdout, stderr, exitCode})` → `{block?, reason?, advisory?}`。

測試（先紅）:
* `exitCode === 2` → `block:true`,`reason` 取 stderr 首行
* stdout JSON `hookSpecificOutput.permissionDecision === "deny"` → `block:true`,reason 取 `permissionDecisionReason`
* stdout JSON `hookSpecificOutput.additionalContext` → `advisory`
* **stdout 是 pass-through 的原輸入**（`{"command":"..."}`）→ 既不 block 也不 advisory ← 最重要的負向案例
* stdout 是壞掉的 JSON → 不丟例外,退回看 stderr
* 只有 stderr → `advisory`
* 全空 → `{}`
* exit 2 與 stdout deny 同時出現 → block 優先,只回一次

### Task 3 · `index.ts` 接線

每個呼叫點:入向 `toHookInput`,出向 `parseHookOutput`。

* pre bash:`block-no-verify`、`gateguard-fact-force`
* pre edit/write:`doc-file-warning`、`suggest-compact`、`config-protection`
* post bash:`post-bash-dispatcher`
* post edit/write:`quality-gate`、`design-quality-check`、`post-edit-console-warn`、`post-edit-accumulator`
* turn_end:`stop-format-typecheck` 等

`notify` 全部保留（受眾是人）。`advisory` 走既有佇列與策略。

守衛測試:`index.ts` 不得再出現 `JSON.stringify(event.input)` 這種裸傳。

### Task 4 · `enableEccGateGuard`（預設 false）

GateGuard 一旦真的接上就會擋 bash,改變日常手感。獨立旗標、預設關閉、由操作者明示開啟。

* `harness-config.json` 新增 `enableEccGateGuard: false` 與 `_enableEccGateGuard` 說明
* 讀取後才把 gateguard 的 `block` 生效;關閉時仍可送 advisory
* 測試:旗標 false → 不 block;true → block
* 必須通過既有的 `test_no_zombie_harness_config_keys`

### Task 5 · 對真實 ECC hook 的整合測試

`tests/test_ecc_hook_contract.py`——這是唯一能抓到「轉譯與上游脫節」的測試層級。

* 以 `toHookInput` 產生 payload,實際 spawn `post-edit-console-warn.js`,斷言 stderr 出現 `console.log found`
* 同一個檔案改用 Pi 的裸 `path` 形狀 → 斷言**沒有**輸出（證明測試抓得到回歸）
* `gateguard-fact-force.js` 收到轉譯後的 bash payload → stdout 含 `permissionDecision: deny`
* `external/ecc` 未初始化時 `skipTest`（CI 上 submodule 可能沒 checkout）

### Task 6 · hello-reflect 解析器

`reflect_core.extract_user_messages` 同時支援兩種格式。

測試（先紅）:
* Pi 形狀（`{"type":"message","message":{"role":"user","content":[{"type":"text","text":"..."}]}}`）→ 取得文字
* Claude Code 形狀（頂層 `role`,content 為字串）→ 仍可取得
* content 有多個 text block → 串接
* 非 user 角色 → 忽略
* 壞行 → 跳過不炸

### Task 7 · Live 驗證

`restore` 後開 pi,一次跑完:

1. 建一個含 `tsconfig.json` 的暫時 repo
2. 提示模型寫一個含 `console.log` 的 `.ts`,再讀回（兩個 turn,turn_end 的建議才有下一個 tool result 可搭載）
3. 在 session JSONL 找 `[ecc-hooks]`,確認 `console.log found` 進入模型可讀的 content block

**修前的對照組已經有了**:同樣的操作,session log 兩個 tool result 各 1 block、無建議。

### Task 8 · 文件

* `docs/KNOWN_ISSUES.md`:記錄「這些守衛以前沒作用,修好後會開始作用」,特別點名 `config-protection`
* `docs/retro/2026-08-04-reported-is-not-received.md`:新增一節,同一個主題的更深一層
* 不動 `CLAUDE.md`——這是具體整合缺陷,不是通則,寫進每輪注入的 prompt 不划算

## Self-Review Notes

* Task 4 的預設值是**刻意保守**:GateGuard 沒被評估過任何一條指令,直接開等於把一個從未在本機跑過的守衛推上線。
* Task 5 是整份計畫的重心。前四個 Task 的單元測試只能證明「我們產出了自己期待的形狀」,只有真的餵給上游腳本才能證明「上游接受這個形狀」——而這正是原本失敗的地方。
* `stop-format-typecheck` 的復活是連鎖效果（accumulator 修好才有輸入),不是獨立任務,列在 Task 7 的觀察項而非斷言項。
