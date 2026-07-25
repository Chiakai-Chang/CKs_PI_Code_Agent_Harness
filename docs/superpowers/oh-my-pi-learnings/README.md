# oh-my-pi 學習筆記索引

> 來源專案：[audreyt/oh-my-pi](https://github.com/audreyt/oh-my-pi)（克隆於 `reference/oh-my-pi`，gitignored）
> 學習目標：從 oh-my-pi 的內部設計決策中學習可適用於本 harness 的改善

## 學習筆記（按主題）

| 文件 | 主題 | 核心收穫 |
|---|---|---|
| [01-hashline-edit-system.md](01-hashline-edit-system.md) | Hashline 雜湊錨定編輯系統 | 內容雜湊快照 + 3-way merge 復原過期錨定 → bridge manifest 完整性驗證概念 |
| [02-resolve-tool-pattern.md](02-resolve-tool-pattern.md) | Resolve 工具模式（Preview/Apply） | SoftToolRequirement 軟提醒哲學、失敗重試保留 |
| [03-context-discovery-system.md](03-context-discovery-system.md) | 統一情境檔案發現系統 | 多提供者優先序 + 向上行走 + Sticky Rules vs Context |
| [04-rulebook-and-skills.md](04-rulebook-and-skills.md) | Rulebook 規則系統與 Skill 發現 | 提供者優先序 + 名稱去重 + managed fallback、按需激活 globs |
| [05-memory-compaction-sessions.md](05-memory-compaction-sessions.md) | 自主記憶、壓縮与会話樹 | 記憶信任等級框架、壓縮邊界保留、租約防多重執行 |
| [06-natives-and-bash-runtime.md](06-natives-and-bash-runtime.md) | Natives 原生架構與 Bash 運行時 | 共享 FS scan cache、版本化二進位快取、主動失效信號 |
| [07-architecture-comparison.md](07-architecture-comparison.md) | 架構對比與本專案差距分析 | 定位差異、5 項關鍵差距、明確排除的不適用設計 |

## 復盤與優化

| 文件 | 內容 |
|---|---|
| [08-review-and-findings.md](08-review-and-findings.md) | 核心收穫適用性評估矩陣（高/中適用性 × 緊急度） |
| [09-optimization-plan.md](09-optimization-plan.md) | 優化工作計畫（A/B/C/D 四項 + 驗證策略） |
| [10-optimization-execution-report.md](10-optimization-execution-report.md) | 執行報告：全部完成，含實測證據 |

## 產生的改善（已落實）

- `pi-extensions/bridge-manifest.json` — bridge 健康度 manifest
- `scripts/verify-bridges.py` — bridge 入口驗證腳本
- `scripts/validate-config.py` — 設定檔 schema 與反模式驗證
- `external-manifest.json` — 外部來源統一記錄
- `pi-extensions/skill-namespace-guard/index.ts` — 升級：跨來源 skill 衝突報告
- `pi-config/settings.json` — 移除硬編碼 Windows shellPath
