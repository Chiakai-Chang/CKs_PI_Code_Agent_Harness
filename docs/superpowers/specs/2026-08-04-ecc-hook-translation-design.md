# ECC hook 轉譯層 Design（2026-08-04）

## 為什麼需要這份設計

驗證「六個 advisory 生產端」時,六個全部不會發射。原因不在 advisory 管線——它是對的,`plan-missing` 走同一條路且有 session log 為證。原因在**更上游**:`ecc-hooks-bridge` 把 Pi 的事件翻譯給 ECC hook 時,用錯了欄位名、少了一層外殼、讀錯了輸出通道。

十五個被消費的 ECC hook 裡,只有 `block-no-verify` 真的在運作——它掃原始文字,所以形狀無關。

這是本 repo 自己第一條禁令 **No Zombie Configs** 的大規模現行犯,而 `README.md`、`docs/core/CORE_CONCEPTS.md`、`docs/core/HARNESS_INTEGRATION_GUIDE.md` 都把 GateGuard、quality-gate 寫成運作中的功能。

## 三個根因（皆有實測）

### 根因一 · 欄位名:Pi 送 `path`,ECC 讀 `file_path`

已安裝 Pi 的 schema:

```
dist/core/tools/write.d.ts:5    path: Type.TString;  content: Type.TString;
dist/core/tools/edit.d.ts:11    path: Type.TString;  edits: [{ oldText, newText }]
```

ECC 這邊:

```
post-edit-console-warn.js:28    input.tool_input?.file_path
quality-gate.js:143             input.tool_input?.file_path
config-protection.js:93         input?.tool_input?.file_path || input?.tool_input?.file
post-edit-accumulator.js:54     input.tool_input?.file_path  (MultiEdit 另讀 edits[].file_path)
doc-file-warning.js             input.tool_input?.file_path
design-quality-check.js:37      file_path
gateguard-fact-force.js:1153    toolInput.file_path
```

同一個檔案,只差欄位名:

```
$ printf '{"tool_name":"write","tool_input":{"path":".../bad.ts"}}' | node post-edit-console-warn.js
（無輸出）
$ printf '{"tool_name":"write","tool_input":{"file_path":".../bad.ts"}}' | node post-edit-console-warn.js
[Hook] WARNING: console.log found in .../bad.ts
```

**連帶災情**:`config-protection` 是會 `exit(2)` 擋下設定弱化的守衛,它也讀 `file_path`——從來沒擋過任何東西。`post-edit-accumulator` 同樣讀不到路徑,於是 `stop-format-typecheck` 永遠拿到空的 accumulator 而早退,形成連鎖。

### 根因二 · bash 少一層外殼

```ts
// index.ts:145  bash
const input = JSON.stringify(event.input);                          // {"command":"..."}
// index.ts:158  edit/write
JSON.stringify({ tool_name: name, tool_input: event.input })        // 有外殼
```

`gateguard-fact-force.js:1145` 讀的是 `data.tool_name` 與 `data.tool_input`。裸形狀進去,兩者皆 undefined,直接原樣回傳。實測同一條 `rm -rf build`:

```
裸  {"command":"rm -rf build"}                          -> 原樣吐回,無判斷
包好 {"tool_name":"Bash","tool_input":{"command":...}}   -> {"permissionDecision":"deny",
      "permissionDecisionReason":"[Fact-Forcing Gate] Destructive command detected..."}
```

**GateGuard 從來沒有評估過任何一條 bash 指令。**

### 根因三 · 輸出通道:部分 hook 用 stdout JSON,bridge 只讀 stderr 與 exit 2

| hook | 實際使用 | bridge 讀 |
|---|---|---|
| `block-no-verify` | `exit(2)` ×2 | exit 2 ✓ |
| `config-protection` | `exit(2)` ×3 | exit 2 ✓ |
| `post-edit-console-warn` | stderr ×3 | stderr ✓ |
| `quality-gate` | stderr ×1 | stderr ✓ |
| `stop-format-typecheck` | stderr ×5 | stderr ✓ |
| `gateguard-fact-force` | **stdout JSON** ×3,`exitCode: 0` | exit 2 ✗ |
| `suggest-compact` | **stdout JSON** ×2 | `stderr.includes("compact")` ✗ |

`suggest-compact.js` 的原始碼註解自己講明了:

```js
// non-blocking PreToolUse stderr (exit 0) is only written to the debug log;
// it does not reach the model. ... emit structured JSON to stdout with
// hookSpecificOutput.additionalContext
```

所以就算修好形狀,GateGuard 仍然擋不住——它回 `exitCode: 0` 加 stdout 的 `permissionDecision: "deny"`。

### 根因四（獨立）· hello-reflect 解析的是 Claude Code 的 session 格式

```
$ python -c "... extract_user_messages(<real pi session>) ..."
exists: True
extract_user_messages -> 0 messages
a real user line: top-level role = None | nested role = user | content type = list
```

`pi-skills/core/hello-reflect/scripts/reflect_core.py:89` 找 `entry["role"]`,Pi 放在 `entry["message"]["role"]`;`:91` 要求 content 是 `str`,Pi 是 block list。**它一則訊息都沒讀過。**

## 設計

### 邊界:不改 submodule

`external/ecc` 是 submodule(上游 `affaan-m/ECC`),`yes-hooks-bridge` 本身就會擋住寫入 vendored submodule。**轉譯是我們這邊的責任**,ECC 的契約視為既定外部介面。

`pi-skills/core/hello-reflect/` 是本 repo 自有,可直接修。

### 新模組:`pi-extensions/ecc-hooks-bridge/ecc-payload.ts`

單一職責:Pi 事件 ↔ ECC hook 契約的雙向轉譯。純函式,可被 node driver 測試,不碰 I/O。

**入向 `toHookInput(toolName, input, output?)`**

| Pi | 產出 |
|---|---|
| `bash` `{command}` | `{tool_name:"bash", tool_input:{command}}` |
| `write` `{path, content}` | `{tool_name:"write", tool_input:{file_path:path, path, content}}` |
| `edit` `{path, edits}` | `{tool_name:"edit", tool_input:{file_path:path, path, edits}}` |
| 有 tool_output 時 | 併入 `tool_output` |

同時保留 `path`:ECC 現在不讀它,但多送一個欄位無害,而且上游若改用 `path` 就不會再斷一次。`tool_name` 用小寫即可——`gateguard-fact-force.js:1148` 的 `TOOL_MAP` 是大小寫不敏感的。

**出向 `parseHookOutput({stdout, stderr, exitCode})` → `{block?, reason?, advisory?}`**

依序判定,先擋後勸:

1. `exitCode === 2` → `{block:true, reason: stderr 首行 || 既定訊息}`
2. stdout 是 JSON 且 `hookSpecificOutput.permissionDecision === "deny"` → `{block:true, reason: permissionDecisionReason}`
3. stdout 是 JSON 且有 `hookSpecificOutput.additionalContext` → `{advisory: additionalContext}`
4. `stderr` 非空 → `{advisory: stderr}`
5. 其餘 → `{}`

stdout 不是 JSON、或是 pass-through 的原輸入(hook 常把輸入原樣吐回)時,不得誤判為建議——用「解析成功且含 `hookSpecificOutput`」當作唯一入口條件。

### 呼叫端改動

`index.ts` 的每個 hook 呼叫點改為:入向用 `toHookInput`,出向用 `parseHookOutput`,再依結果 `advisories.push(...)` 或 `return { block, reason }`。`notify` 維持不變(受眾是人)。

### hello-reflect 解析器

`reflect_core.extract_user_messages` 同時支援兩種格式:

* Claude Code:頂層 `role`,content 為字串
* Pi:`entry["message"]["role"]`,content 為 block list,取 `type == "text"` 的 `text` 串接

保留舊格式,因為這個 skill 是從 claude-reflect 蒸餾來的,不排除在別處被餵 Claude Code 的紀錄。

### 不做

* **不改 `external/ecc`**——submodule,且轉譯本來就該在我們這側。
* **不預設開啟 `ECC_QUALITY_GATE_STRICT`**——那是 ECC 的預設值決定的行為,改它等於替使用者決定嚴格度。改為在文件記錄「要 quality-gate 出聲就得設這個環境變數」。
* **不重寫 gateguard 的判定邏輯**——只把它的決定接回來。

## 風險

* **GateGuard 一修好就會開始擋 bash**。它是 fact-forcing gate,對破壞性指令要求先列出影響。這會改變日常操作手感。緩解:與 advisory 共用 `enableHookAdvisories`?不行——擋和勸是不同語意。改為新增獨立旗標 `enableEccGateGuard`,預設 **false**,由操作者明示開啟。這條在計畫裡是獨立任務。
* **`config-protection` 一修好也會開始擋編輯**。它擋的是設定弱化,語意上是安全守衛,預設開啟合理,但要在 retro 與 KNOWN_ISSUES 講明「這條以前沒作用,現在會作用了」。

## 驗證方式

每一項都要有「刻意弄壞會紅」與「live session log 為證」兩層:

1. 單元:`toHookInput` / `parseHookOutput` 的純函式測試,含 pass-through stdout 不得誤判。
2. 整合:直接以 bridge 的方式呼叫真實 ECC hook,斷言 `post-edit-console-warn` 對 Pi 形狀會吐 stderr(修前不會)。
3. Live:一次 `pi --print` 讓模型寫一個含 `console.log` 的 `.ts` 再讀回,於 session JSONL 找到 `[ecc-hooks]` 區塊。
