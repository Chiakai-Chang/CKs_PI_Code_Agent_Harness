# 保留的 session 紀錄

任務包引用的證據原本只存在於 session 專屬的暫存目錄裡 —— 那些目錄會被清掉,
而清掉之後,`docs/case/` 裡的每一段引用就變成無法複驗的轉述。這裡放的是決定性的幾份原始檔。

| 檔案 | 證明什麼 |
|---|---|
| `2026-08-06-guard-block-visible-in-log.jsonl` | 擋阻會以 `role: toolResult` + `isError: true` 寫進逐字稿(Task_008 第 0 步的儀器檢查);同一份也記錄了模型被擋後**謊報完成** |
| `2026-08-06-blocked-claim-silent-before-fix.jsonl` | 修正通道**之前**:謊報發生、矯正**沒有**注入 |
| `2026-08-06-blocked-claim-delivered.jsonl` | 修正**之後**:謊報 → `customType: "blocked-claim"` 注入 → 模型 `cat` 驗證 → 對使用者更正 |

讀法(避免子字串猜測,依 `message.role` / `toolName` 過濾):

```bash
python - <<'PY'
import json
for line in open("docs/measurements/sessions/2026-08-06-blocked-claim-delivered.jsonl", encoding="utf-8"):
    d = json.loads(line)
    if d.get("customType"): print(d["customType"], "->", d["content"][:60])
PY
```

**這三份都是本機探針專案的紀錄,不含任何真實工作內容。**
