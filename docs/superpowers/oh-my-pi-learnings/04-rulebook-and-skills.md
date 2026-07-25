# oh-my-pi 學習筆記：Rulebook 規則系統與 Skill 發現管道

> 來源：`reference/oh-my-pi/docs/rulebook-matching-pipeline.md`、`docs/skills.md`

## Rulebook 規則系統

oh-my-pi 將多套設定格式（`.omp/RULES.md`、Cursor `.cursorrules`、Windsurf 等）統一為規範化的 `Rule` 形狀：

```ts
interface Rule {
  name: string; path: string; content: string;
  globs?: string[]; alwaysApply?: boolean; description?: string;
  condition?: string[]; astCondition?: string[]; scope?: string[];
  interruptMode?: "never"|"prose-only"|"tool-only"|"always";
}
```

- **去重鍵**：僅依 `name`，同名即視為同一邏輯規則
- **提供者優先序**：native(100) > omp-plugins(90) > agents(70) > cursor(50)
- **TTSR 分流**：部分規則轉為 Time Traveling Stream Rules（長對話中重新注入）
- **內建規則庫**：`builtin-rules/` 目錄包含語言特定最佳實踐（`ts-no-any.md`、`go-ioutil.md` 等），以 `alwaysApply: false` + `globs` 按需激活

## Skill 發現管道

三階段發現：

1. **能力提供者**（`loadCapability("skills")`）：native(100) > omp-plugins(90) > claude(80) > agents/codex(70) > github(30)
2. **自訂目錄**：`skills.customDirectories`，非遞迴掃描 `*/SKILL.md`
3. **Managed（自動學習）技能**：`omp-managed` 提供者（優先序 5），最後載入，同名作者 skill 永遠優先

- 發現路徑：**非遞迴** — `<skills-root>/<skill-name>/SKILL.md` 才被發現，嵌套目錄忽略
- `description` 在 `.omp` / plugin / github 提供者中為必填
- `skill://<name>` URL 協議讓模型按需讀取 skill 內容

## 對本專案的啟發

### 直接可用
- **Skill 命名衝突防護**：我們的 `pi-skills/` 結構是遞迴的（`core/`、`optional/`、`chrome-cdp/`），而 oh-my-pi 用非遞迴 + 名稱去重。本專案的 `skill-namespace-guard` bridge 正是為解決此問題而生，但可借鑑 oh-my-pi 的提供者優先序 + 名稱去重設計，讓衝突解析更明確。
- **按需激活**：oh-my-pi 的 `globs` + `alwaysApply: false` 模式值得學習 — 我們的 skill 目前全數註冊、全數可見，增加情境噪音。可引入條件激活（如 `chrome-cdp` 僅在有 Chrome 時激活）。
- **內建規則庫概念**：oh-my-pi 的 `builtin-rules/` 是語言特定最佳實踐庫。我們的 `pi-rules/` 目錄已有類似內容，但缺少 glob 匹配和條件激活機制。

### 概念借鑑
- **Managed skill 層級**：oh-my-pi 的自動學習技能（優先序 5）永遠讓位於作者 skill，但可補充使用者未手動配置的領域。這為「AI 自生成 skill」提供了安全位置 — 不會覆蓋有意識的作者內容。
- **`skill://` URL 協議**：統一內部 URL 協議讓 skill 內容可被 `read` 工具、bash 命令、env 變數等一致存取。

### 改善空間（oh-my-pi 自身）
- 非遞迴 skill 發現限制了技能組織彈性，需用 `customDirectories` 補救。
- 規則去重僅依名稱，不同檔案同名即視為同一規則 — 可能意外遮蔽有意區分的同名規則。
