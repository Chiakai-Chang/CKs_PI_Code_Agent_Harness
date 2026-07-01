# 🧠 決策紀錄 (Rationale) - Loopy Bridge

## 1. 為什麼要引進 Loopy？
在開發複雜且具重複性質的任務（如：優化測試覆蓋率、文檔同步、依賴升級、代碼審查）時，給予 Agent 一個開放式的 Prompt 常會造成漫無目的的重試或失控。
引進 `Forward-Future/loopy` 的核心目的在於：
*   **循環工程 (Loop Engineering)**：將一次性的指令，重構為包含「觀測 -> 動作 -> 驗證 -> 終止」的閉環 Playbook。
*   **終止與降級防禦 (Bounded Autonomy)**：明確規範什麼時候該退出、什麼時候該向人類求助，避免死循環。
*   **發現與審計流程 (Discover & Audit)**：自動從開發歷史與代碼中發現重複工作，將其轉化為 Bounded Loops。

---

## 2. 與既有自適應/修復迴圈（SkillClaw & SkillOpt）的關係與協同

我們目前已導入 `SkillClaw`（高德集體演進）與 `SkillOpt`（微觀除錯自修復）。它們與 `loopy` 的關係為**垂直分層結構，互補運作**：

```text
               +-------------------------------------------+
               |          AI 代理演進與控制架構             |
               +----------------------+--------------------+
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
[ 頂層演進腦: SkillClaw ]      [ 中層工作流: Loopy ]       [ 底層微觀控制器: SkillOpt ]
- 任務：收集 session 軌跡，    - 任務：執行重複業務 Playbook  - 任務：在單次執行工具或
  動態更新/去重 SKILL.md。       (如 docs sync) 的閉環判定。   Debug 時，防範工具死循環。
- 週期：跨 Session、多人。     - 週期：單次完整任務。       - 週期：單次轉向 (Turn)。
```

### ➔ 擇一還是各取優點？
**三者各司其職，形成一個完整的「微觀自校正 (SkillOpt) ➔ 中觀工作流控制 (Loopy) ➔ 宏觀自演進 (SkillClaw)」防禦鏈，必須全部保留：**
1.  **微觀層面 (SkillOpt)**：當 Agent 在寫代碼或運行 command 報錯時，使用 **Rejected Memory** 記錄失敗，並設定 **3擊出局**。
2.  **中觀層面 (Loopy)**：處理像是「同步所有 markdown」這種批處理業務時，Loopy 規定必須回答**四個問題（目標、檢驗、學習行為、終止條件）**，保證業務流程的確定性。
3.  **宏觀層面 (SkillClaw)**：當以上所有循環運行完畢後，背景自動將 Trajectories 送入 Evolver 更新技能庫。

---

## 3. 戰略整合路徑：SO + WO 混合策略 (子模組 + 本地 Rules)
根據 `DISTILLATION_GUIDE.md`：
1.  **原生映射 (Path 1)**：引進子模組 `external/loopy`，將 `loopy-playbooks` 技能註冊至 Pi。
2.  **規則蒸餾**：在 [AGENTS.md](file:///D:/Myproject/CKs_PI_Code_Agent_Harness/pi-rules/AGENTS.md#L23) 的 `Self-Correction & Bounded Optimization` 區段，將其「明確四問」與 `SkillOpt` 的「三擊出局」規則完美融合成一套強大的 **Loop Engineering 規則**。
