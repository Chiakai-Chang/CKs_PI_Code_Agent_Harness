# 分層技能註冊（Tiered Skill Registration）設計

**日期**：2026-07-28
**問題**：Pi 的 `formatSkillsForPrompt` 把**每個**已註冊技能的 name + description + **絕對路徑**寫進**每一輪** system prompt。實測 145 個技能 = 55,239 chars（~13,809 tokens/輪），佔整份 system prompt 的 58%。

---

## 一、量測先於設計

掃過使用者全部 56 個 session、2,315 個 assistant 回合，比對哪些技能的 `SKILL.md` 真的被 `read` 過：

```
registered skills          145    55239 chars  ~13809 tok/turn
  ever loaded               55    23037 chars  ~ 5759 tok/turn   (37.9%)
  never loaded              90    32202 chars  ~ 8050 tok/turn   (62.1%)
```

用最多的是方法論骨幹（`agents-best-practices` 4×、`camofox-stealth` 4×、`brainstorming` / `writing-plans` / `case-framework` / `systematic-debugging` / `hello-reflect` 各 3×）——**證明本 harness 的核心設計確實會被觸發，不是擺設**。從沒載入的 90 個多為領域包（`django-security`、`defi-amm-security`、`evm-token-decimals`…）。

## 二、候選方案與實測數字

| 方案 | 每輪成本 | 省下 |
| :--- | ---: | ---: |
| 現狀（145 全原生註冊） | ~13,809 tok | — |
| B：全部保留，描述截短至 150 字 | ~11,431 tok | 2,378 |
| B：全部保留，描述截短至 100 字 | ~10,237 tok | 3,572 |
| **A：核心 55 完整 + 長尾 90 名稱目錄** | **~6,217 tok** | **7,592** |

**關鍵結構事實**：每個技能的固定開銷（XML 標籤 ~90 chars + 絕對路徑 ~83 chars + 名稱）約 213 chars，佔 55,239 的一半以上。描述中位數只有 168 字。

> **只要一個技能還被 Pi 原生註冊，最低成本就是 ~213 chars，截短描述動不到它。**
> 因此「截短描述」這個看似較安全的替代方案實質無效（省不到 18%），A 案是唯一有效槓桿。
> 附帶：光是 `<location>` 絕對路徑就吃掉 3,024 tok，且由引擎控制、無法改。

## 三、設計

### 3.1 分層規則（config 驅動）

`pi-config/harness-config.json` 新增：

```json
"skillTiers": {
  "mode": "tiered",
  "core": ["<skill-name>", "..."],
  "alwaysCore": ["camofox-stealth", "..."]
}
```

* `mode: "all"` → 回到今日行為（全部原生註冊）。**一行改回，不可逆風險歸零。**
* `mode: "tiered"` → `core` 清單內的原生註冊（保留完整 description，Pi 的原生發現路徑不變）；其餘寫進目錄。
* 核心清單由用量數據 seed，但**是人可編輯的白名單**，不是自動推導——用量數據是回顧性的，不該讓它單方面決定未來。

### 3.2 長尾如何維持可發現

由 `skill-catalog-bridge` 在 `before_agent_start` 注入一份**行內名稱清單**：

```
[Skill Catalog] 以下 90 個特化技能未展開描述以節省 context。
若任務符合其名稱，用 read 工具載入 <harness>/pi-config/skill-catalog.json 取得路徑與描述後再讀 SKILL.md。
adversary-review, agent-architecture-audit, ai-regression-testing, ...
```

**為何用行內名稱、而不是再包一層「索引技能」**：
索引技能只花 ~95 tok（比行內清單的 ~840 tok 便宜），但要求模型**主動決定去讀它**。本 harness 的主要使用情境是弱本地模型，而本次事故的根因正是弱模型不做預期動作。多付 745 tok 讓名字**無條件出現在眼前**，是買掉主要風險，不是浪費。

### 3.3 失效模式（刻意選擇）

* `skill-catalog.json` 讀不到 / `skillTiers` 解析失敗 → **fail open**：全部原生註冊 + 印警告。
  沿用 `ecc_skill_paths()` 的同一個判斷：靜默弄丟全部技能，比 prompt 變胖嚴重得多。
* 核心清單裡列了不存在的技能名 → 測試擋下（同 `ECC_ALWAYS_SKILLS` 的存在性檢查）。

### 3.4 未驗證假設 → 必須實測

> **注入名稱清單後，模型是否仍會找到並載入長尾技能？**

**這是本設計唯一沒有證據支撐的一步。** 本次事故的教訓是「在錯的 runtime 驗證會產出很有說服力的錯誤結論」，因此：

* 用**使用者的本機模型**、在**真正的 Pi 裡**跑 A/B，不用 node 模擬、不用雲端模型代打。
* 探針擴充必須排在注入鏈**最尾端**才看得到完整 prompt。
* 若實測顯示觸發率不可接受，`mode: "all"` 一行回復，且該負面結果要寫進復盤——**負面結果也是結果**。

## 四、不做什麼

* 不刪任何技能檔案。分層只影響「是否展開進 prompt」，`external/` 內容一個字不動。
* 不自動依用量增刪核心清單。自動化一個回顧性指標會讓罕用但關鍵的技能慢慢消失。
* 不動 `<location>` 路徑格式（引擎控制）。
