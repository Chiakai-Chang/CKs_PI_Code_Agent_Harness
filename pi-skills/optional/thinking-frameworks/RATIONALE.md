# RATIONALE: thinking-frameworks

## 決策脈絡
評估 7 個「名人蒸餾人格」repo 後全部否決(見 `docs/decisions/2026-07-09-persona-skills-evaluation.md`)。使用者要「那批 repo 想指向、但乾淨」的版本 = 心智模型當推理工具、不冒名真人。

## 為何做(路徑判定:原生撰寫 clean-room)
- **gap 屬實**:全 skill 空間查證,西方決策心智模型/認知偏誤無人涵蓋(`qiushi` 是辯證法;`recursive-decision-ledger`/`architecture-decision-records` 只管記錄決策)。
- **與既有分工**:`mece-autopilot` = 重量級群體對抗辯論(複雜取捨);本 skill = 日常小決策的快速個人透鏡,重取捨升級 mece;`qiushi` = 辯證分析。三者不同量級、互補。
- **無責任**:不冒名任何真人、不給投資/醫療/法律建議,避開名人人格 repo 的 IP/冒名/建議責任。

## 設計脈絡(dogfood qiushi+mece)
初版設計「不加觸發以免撞 mece」被 mece 魔鬼代言人揪出致命弱點:無觸發 = 沒人用 = 裝飾。重塑為「mece 之下的快速透鏡」:靠 skill 自身「何時用」引導、重取捨明文升級 mece,取得非重疊生態位。

## 維護
純 Markdown、零依賴、無外部上游。內容穩定,少需更動;新增框架時保持「高信號、可即用」,勿膨脹成百科。
