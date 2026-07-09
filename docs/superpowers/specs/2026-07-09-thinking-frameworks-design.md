# thinking-frameworks Skill 設計 (2026-07-09)

> 一個**無冒名**的思考工具 skill：把西方決策心智模型當快速個人自我檢查,補 `qiushi`(辯證法)與 `mece-autopilot`(對抗辯論)沒涵蓋的那一味。

## 背景與決策脈絡
評估 7 個「名人蒸餾人格」repo 後全部否決(見 `docs/decisions/2026-07-09-persona-skills-evaluation.md`)。使用者要「那批 repo 想指向、但乾淨的版本」= 心智模型當推理工具、不冒名任何真人。

用 harness 自身的推理工具(qiushi + mece)檢驗本提案,得三個關鍵發現:
1. **調查(qiushi):** 全 skill 空間 grep 確認,西方心智模型/認知偏誤/決策啟發**確實無人涵蓋**(qiushi 是辯證法;`recursive-decision-ledger`/`architecture-decision-records` 只管記錄決策)。gap 屬實。
2. **致命弱點(mece 魔鬼代言人):** 原設計「不加觸發以免撞 mece」= 沒人提醒用 = 純裝飾(指南 anti-pattern)。
3. **解方:定位到 mece 不佔的生態位。** mece = 重量級群體對抗辯論(複雜取捨才出動);本 skill = **日常非瑣碎小決策的快速個人自我檢查**,重取捨則升級 mece。不同量級、互補不重疊。

## 目標 (Goal)
在做日常非瑣碎的判斷/取捨時,提供一份簡短、高信號的西方決策模型清單,強制快速過一遍以減少盲點;複雜取捨明確導向 `mece-autopilot`。

## 非目標 (Non-Goals)
- 不冒名/扮演任何真實人物。
- 不給投資/醫療/法律建議。
- 不取代 mece(群體辯論)或 qiushi(辯證法);不做全域強制 rule 與 mece 觸發打架。
- 不做成百科全書——只收高信號、可即用的核心工具。

## Global Constraints
- **零冒名**:不得出現「扮演 <真人>」「act as <person>」等字樣或真人人格。
- **零建議責任**:明文標示純推理工具,非投資/醫療/法律建議。
- 純 Markdown skill,零依賴;測試用 `unittest`(不引入 pytest)。
- 中文用臺灣正體(與 harness 一致);不硬編機器路徑。
- 分工明文:重取捨 → mece;辯證分析 → qiushi;本 skill = 快速個人透鏡。

## 放置與載入
- 位置:`pi-skills/optional/thinking-frameworks/{SKILL.md, RATIONALE.md}`。
- **層級 = standard(非 core)**:放 `optional/` → restore 於 standard profile 複製、minimal 不吃(honors「不加重 minimal」)。pi 自動掃描 `~/.pi/agent/skills/` 載入,**無需改 restore.py / settings.json**(與既有 `camofox-stealth`/`nothing-design` 同機制)。

## 元件

### SKILL.md
- **frontmatter**:`name: thinking-frameworks`;description 壓 1–2 行,講「日常非瑣碎決策的快速心智模型自我檢查;重取捨用 mece」。
- **何時用**:快速非瑣碎判斷/取捨/評估時過一遍;若牽涉多方利害、複雜取捨 → 升級 `mece-autopilot`。
- **7 個工具**(各一句怎麼套):
  1. **反演**:什麼會保證失敗?→ 避開它。
  2. **基準率 / 外部視角**:同類事情一般結果的機率是多少?別只信眼前這個故事。
  3. **二階效應**:這步之後會連鎖出什麼?(不只看直接結果)
  4. **機會成本**:做這個 = 放棄了什麼更好的?
  5. **第一性原理**:拆到根本事實重建,而非照類比/慣例。
  6. **認知偏誤檢查**:確認偏誤、沉沒成本、錨定、過度自信、可得性——中了沒?
  7. **可證偽**:什麼證據會讓我改變主意?(強迫找反證,不只找支持)
- **邊界**(明文區塊):純推理工具;不冒名真人;不給投資/醫療/法律建議;與 qiushi/mece 的分工。

### RATIONALE.md
記錄:為何做(補確認過的西方心智模型 gap)、與 qiushi/mece 的分工、為何無冒名無責任、以及「用兩套工具檢驗後如何重塑設計(從裝飾→快速透鏡)」的脈絡。路徑判定:原生撰寫(clean-room),非蒸餾自任何 repo。

## 測試(`tests/test_thinking_frameworks.py`,unittest 零依賴)
- `SKILL.md` 存在;frontmatter `name: thinking-frameworks`。
- 含 7 個框架關鍵字:反演、基準率、二階、機會成本、第一性、偏誤、可證偽。
- 含分工字樣:提到 `mece`(升級重取捨)與 `qiushi`。
- **邊界斷言(正向)**:含「不冒名」「純推理工具」「非投資」等明文邊界字樣(避免用「不含扮演」這種會被邊界宣告本身誤判的反向斷言)。
- **反冒名斷言(安全樣式)**:不得出現「我是 <真人名>」「作為 <真人名>」「You are <RealPerson>」這類第一人稱扮真人指令——測試以具體樣式檢查(如不出現 `我是巴菲特`、`作為巴菲特`、`扮演巴菲特`),而非泛詞。
- 平台無關:無機器路徑。

## 檔案清單
- 新增:`pi-skills/optional/thinking-frameworks/SKILL.md`、`.../RATIONALE.md`、`tests/test_thinking_frameworks.py`
- (無需改 restore.py / settings.json)

## 驗證
- `python -m unittest discover -s tests` 全綠。
- 沙盒 restore(standard)後 `~/.pi/agent/skills/thinking-frameworks/SKILL.md` 存在;minimal profile 下不存在。
- `grep -rn "act as\|扮演" pi-skills/optional/thinking-frameworks` 無冒名命中。
