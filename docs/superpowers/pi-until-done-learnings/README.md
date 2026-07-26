# pi-until-done 學習筆記索引

> 來源專案：[srinitude/pi-until-done](https://github.com/srinitude/pi-until-done)（克隆於 `reference/pi-until-done`，gitignored）
> 定位：Pi 擴充套件，「durable, evidence-driven goal pursuit」— `/until-done` 將意圖轉為經 LLM judge 驗證的合約化目標
> 學習目標：從其將開發原則轉化為可執行機制的模式中學習

## 學習筆記（按主題）

| 文件 | 主題 | 核心收穫 |
|---|---|---|
| [01-evidence-driven-completion-system.md](01-evidence-driven-completion-system.md) | 證據驅動完成系統（Judge + Verifiability Block） | Judge 分離驗證、fail open with visible warning → CLAUDE.md「實測有證據」的注入化 |
| [02-bounded-execution-and-spin-detection.md](02-bounded-execution-and-spin-detection.md) | 有界執行與空轉偵測 | agent_settled 狀態機、turn budget、spin guard → compact-continuation 的停止條件概念 |
| [03-session-state-and-hook-discipline.md](03-session-state-and-hook-discipline.md) | Session 原生狀態與 Hook 組合紀律 | typed custom entries + reducer replay、hook 模組化架構 → bridge hook 使用紀律文件 |
| [04-compaction-survival-and-tool-patterns.md](04-compaction-survival-and-tool-patterns.md) | Compaction 生存套件與工具註冊模式 | verbatim preservation 區塊設計 → compact-continuation-bridge 重構 |
| [05-tdd-model-and-upstream-lockstep.md](05-tdd-model-and-upstream-lockstep.md) | TDD 執行模型與上游版本鎖定自動化 | pi-config operating contract 繼承、fail closed on version skew → bridge API 分歧調查 |

## 復盤與優化

| 文件 | 內容 |
|---|---|
| [06-review-and-findings.md](06-review-and-findings.md) | 核心收穫適用性評估矩陣 |
| [07-optimization-plan.md](07-optimization-plan.md) | 優化工作計畫（A/B/C/D 四項） |
| [08-bridge-api-divergence-migration-plan.md](08-bridge-api-divergence-migration-plan.md) | Bridge API import 分歧調查與遷移計畫（待 Pi 運行時驗證） |
| [09-optimization-execution-report.md](09-optimization-execution-report.md) | 執行報告：A/B/C 完成，D 調查完成待驗證 |

## 產生的改善（已落實）

- `pi-extensions/compact-continuation-bridge/index.ts` — compaction survival kit：verbatim preservation 區塊 + 實測紀律注入 + hook 選擇理由文件化
- `pi-extensions/planning-with-files-bridge/index.ts` — verifiability block：每輪注入 HARD discipline（代理信號拒絕、不確定性視為未完成、引用實際輸出）
- `pi-rules/extension-hook-discipline.md` — hook 組合紀律強制政策文件（規則、參考表、已知陷阱）
