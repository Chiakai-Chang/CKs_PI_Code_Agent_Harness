# 決策記錄:名人蒸餾人格 Skills 評估 (2026-07-09)

**狀態:** 已決定 — 全部否決 (Power of No)
**方法:** DISTILLATION_GUIDE §1 SWOT/TOWS + 研究隔離 (§6)。7 個候選 repo 各派一個並行研究 agent 產 dossier,依統一 rubric 評分。

## 問題
本專案已整合 `mece-autopilot`(模擬角色辯論)。是否應再加入以下「將名人蒸餾成人格」的 skill repo,對 coding harness 有幫助?

## 逐 repo 判定(全 REJECT)
| repo | 一句話 |
|---|---|
| [nuwa-skill](https://github.com/alchaincyf/nuwa-skill) | 14 個固定名人角色扮演,含 Trump/孫宇晨等爭議真人;僅 1 個沾 coding。 |
| [tianya-skills](https://github.com/momozi1996/tianya-skills) | 20 個論壇名人智庫(僅 5 個完成),房產/人生/歷史建議,零 coding。 |
| [ai-berkshire](https://github.com/xbtlin/ai-berkshire) | 硬綁 Buffett/段永平/李錄輸出買賣/目標價建議,理財 + 冒名責任。 |
| [investment-master-mindset](https://github.com/Cat-Geek/investment-master-mindset) | 第一人稱扮真人投資者、強制「不准跳出角色」,責任更重、無 License。 |
| [agency-agents](https://github.com/msitarzewski/agency-agents) | 230+ 固定角色農場;唯一可抽的 code-review 嚴重度/格式慣例,本專案已有。 |
| [system_prompts_leaks](https://github.com/asgeirtj/system_prompts_leaks) | 洩漏的商用 system prompt 集(含上游 Anthropic/Claude Code),IP/法律曝險;非人格、無方法價值。 |
| [awesome-persona-distill-skills](https://github.com/xixu-me/awesome-persona-distill-skills) | 3 個月新、未審的 71 條連結目錄,~90% 與開發無關;相關少數帶真人冒名/理財責任。 |

## 三個一再出現的否決理由
1. **與 mece-autopilot 重疊且為退化版。** 本專案已有「多視角逼出盲點」的**更好版本**:mece **動態**生成互斥專家 + SWOT/TOWS,不綁死名人、無冒名/責任問題。固定名人人格恰恰違反 mece 的「拒絕套用固定角色」設計原則。
2. **對 coding agent 幾乎無用。** 指南唯一移植理由是「顯著提升**開發**效率」。投資/名人/命理型人格過不了這關(多數 coding 相關性 = Low)。
3. **冒名 + IP + 理財建議責任。** 真實在世名人(Buffett、Trump、Soros…)與洩漏商用 prompt,整進 MIT 散布專案 = 實質法律/道德風險。正中 DISTILLATION_GUIDE Anti-Bragging 第 1 課點名的「大師級資產」浮誇痛點。

## 決定
**一個都不加。** 整個「固定名人蒸餾人格」品類對本 coding harness 是負資產。所需能力(對抗式多角色推理)已由 `mece-autopilot` 以更乾淨、無責任的方式提供。

## 給未來的可複用準則(persona-skill 提案篩選閘)
收到任何「名人/專家人格」skill 提案時,依序問:
1. 對 **coding/開發** 有無直接幫助?否 → 拒。
2. 是否只是 `mece-autopilot` 動態角色的**固定退化版**?是 → 拒。
3. 是否模擬**真實在世名人**、或含**洩漏/專有內容**、或給**投資/醫療/法律建議**?任一是 → 拒(責任)。
4. 通過上述才進 SWOT/TOWS 評估路徑。

研究 dossier 為一次性產物,依研究隔離原則未進版控(`research/` 已 gitignore)。
