---
name: skillclaw
description: "Use for collective skill evolution, auditing skill registry, or running/managing the SkillClaw server and dashboard to aggregate session memories."
---

# 🧬 智慧演進與去重 (SkillClaw)

`SkillClaw` 是一個跨會話 (cross-session)、跨代理人 (cross-agent) 的技能演進與精簡去重系統。它能將不同會話中沉澱下來的 `SKILL.md` 規則進行分析、合併、去重與最佳化，維持 Harness 的輕量與高品質。

## ⚙️ 核心指令

在終端機中，你可以透過以下方式運行 SkillClaw（將自動偵測並調用本地的 python/pip 依賴）：

```bash
# 啟動 SkillClaw 背景守護行程 (Daemon) 與 API 服務
python -m skillclaw start --daemon

# 啟動本地的去重與演進視覺化儀表板 (Dashboard)
python -m skillclaw dashboard

# 手動執行一輪技能演進與合併 (Evolves skills collectively)
python -m skillclaw.skill_manager evolve --sessions-dir ~/.pi/agent/sessions --skills-dir ~/.pi/agent/skills

# 查看目前技能註冊清單與版本狀態
python -m skillclaw status
```

## 🧭 執行準則

1.  **定期清理與去重**：當發現本地 `pi-skills` 或 `~/.pi/agent/skills` 下累積了大量類似或重複的 `SKILL.md` 檔案時，主動建議或執行 `evolve` 指令將它們進行結構性合併。
2.  **避免重複定義**：在新增任何全新 Skill 前，先運行 `python -m skillclaw status` 或檢索既有 skills，確保沒有功能重疊的舊 Skill。
3.  **無痛背景運作**：在長期或複雜的多任務開發中，可開啟 `python -m skillclaw start --daemon` 讓系統自動搜集會話軌跡，自動提煉最佳實踐。
