# pi-until-done 學習後優化執行報告

> 執行 `07-optimization-plan` 的實作記錄。遵循 CLAUDE.md「實測有證據」原則。

## 執行摘要

| 工作項 | 狀態 | 新增/修改檔案 |
|---|---:|---|
| A. Compaction 生存套件升級 | ✅ 完成 | `pi-extensions/compact-continuation-bridge/index.ts`（重構） |
| B. Verifiability Block 注入 | ✅ 完成 | `pi-extensions/planning-with-files-bridge/index.ts`（升級） |
| C. Hook 紀律文件化 | ✅ 完成 | `pi-rules/extension-hook-discipline.md`（新增） |
| D. Bridge API import 統一 | 🟡 調查完成，遷移待驗證 | `docs/superpowers/pi-until-done-learnings/08-bridge-api-divergence-migration-plan.md`（新增） |

## A. Compaction 生存套件升級

### 實作內容
重構 compact-continuation-bridge 的 CONTINUE_MESSAGE：
- 新增 verbatim preservation 區塊標頭 `"[compact-continuation · compaction context — preserve everything below verbatim]"`，指導 Pi 的 lossy compaction 保留此內容
- 注入實測紀律條文（「完成聲明必須有實際命令輸出作為證據」）— 將 CLAUDE.md 原則帶過 compaction 邊界
- 註解文件化 hook 選擇理由（為何用 session_compact 不用 session_before_compact）與設計來源（pi-until-done compaction-context.ts）
- 註解說明與 planning-with-files-bridge 的協作關係（plan context 由後者 via before_agent_start 注入，本 bridge 不需重複）

### 實測證據
```
$ node --check pi-extensions/compact-continuation-bridge/index.ts
exit: 0
```

## B. Verifiability Block 注入

### 實作內容
在 planning-with-files-bridge 的 `injectPlanContext()` 函數末尾附加 verifiability block：
- 四條 HARD discipline 文字（代理信號拒絕清單、不確定性視為未完成、引用實際命令輸出、完成前清理）
- 經 `before_agent_start` hook 每輪注入 system prompt — agent 執行時可見，非僅開發者指南中的 prose
- 來源註明：adapted from pi-until-done's verifiability block + CLAUDE.md Evidence-Based Completion

### 實測證據
```
$ node --check pi-extensions/planning-with-files-bridge/index.ts
exit: 0
```

## C. Hook 紀律文件化

### 實作內容
新增 `pi-rules/extension-hook-discipline.md`：
- 四條組合規則（system prompt append only、uninvolved return undefined、hook choice documented、no session control from events）
- Hook 選擇參考表（8 個 hooks 的用途與禁用場景）
- 三個已知陷阱文件化（session_before_compact ineffective、agent_end vs agent_settled、overflow double-up）— 前兩項來自 nunorralves 文章與 pi-until-done README，第三項是 compact-continuation-bridge 自身已實作的防護
- 來源引用 Pi 官方文件、nunorralves 文章、pi-until-done Runtime contract

## D. Bridge API import 統一（調查完成）

### 實查結果
npm registry 確認 `@mariozechner/pi-coding-agent`（oh-my-pi fork）凍結於 0.73.1（2026-05-07），`@earendil-works/pi-coding-agent`（上游 Pi）活躍於 0.82.1（2026-07-25）。5 個 bridge 使用凍結 fork，ecc-hooks-bridge 有 value import `isToolCallEventType` 需確認上游存在性。

### 為何未直接遷移
遷移需要 Pi 運行時 session 測試驗證（步驟 4）— 無法在本 repo 工具鏈中完成。無驗證的 API 變更違反「實測有證據」原則。詳細調查與遷移步驟記錄於 `08-bridge-api-divergence-migration-plan.md`。

## 驗證與一致性

```
$ python scripts/verify-bridges.py
Bridge verification complete: 9 bridges checked, 0 failure(s) found.

$ python scripts/validate-config.py
Config validation complete: 0 failure(s) found.
```

## pi-until-done 學習成果總結

本次從 pi-until-done 學習的核心設計決策：
1. **Verifiability block per-turn injection** → 轉化為 planning-with-files-bridge 的系統 prompt 注入，將「實測有證據」從口號變紀律
2. **Compaction survival kit** → 轉化為 compact-continuation-bridge 的 verbatim preservation 區塊設計
3. **Hook composition discipline** → 轉化為 pi-rules/extension-hook-discipline.md 強制政策文件
4. **Upstream lockstep + version pinning** → 轉化為 bridge API 分歧調查與遷移計畫（待驗證執行）

未移植的設計（明確排除）：完整 judge 系統、Ralph loop、Pi 工具註冊、session-native state reducer — 均為 agent 擴充套件層職責。
