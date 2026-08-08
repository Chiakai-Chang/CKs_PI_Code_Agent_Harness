# 2026-08-08 推進器重測:迴圈接起來了,而開場那一擊仍然穿過去

**判定:`enableCaseAdvancer` 的證據反轉了 —— 但預設值先不動,因為量到一個門檻缺陷。**

| | |
|---|---|
| 模型 | `GRM-3.2-Sky-ONYX-balanced.gguf`,n_ctx 262144,`--temp 1.0` |
| 旗標 | 量測期間 `true`,量完 `git checkout` 還原並確認 `git status` 乾淨 |
| 佇列 | 量測期間**移出 repo**(不是改名) |
| 提示 | 基準線與研究型,**逐字**取自 2026-08-06 的紀錄 |
| fixture | `bootstrap.py` 建的**真** C.A.S.E. 專案(見下,第一版不是) |

## 結果:4/4 走到 REVIEW

| run | 提示 | 輪次 | 工具 | 擋阻 | 推進注入 | status 寫入(工具/bash) | 終態 | 任務包 |
|---|---|---|---|---|---|---|---|---|
| 1 | 基準線 | 18 | 19 | 4 | 3 | **2 / 0** | `REVIEW` | 完整 |
| 2 | 基準線 | 17 | 17 | 2 | 2 | **2 / 0** | `REVIEW` | **缺 `output.md`** |
| 3 | 基準線 | 15 | 16 | 2 | 3 | **2 / 0** | `REVIEW` | 完整 |
| 4 | **研究型** | 31 | 46 | 17 | 5 | **2 / 0** | `REVIEW` | 完整 |

對照 2026-08-06:**5 次 run 沒有一次到 DONE,三次 ESCALATED。** 現在 4/4 到 REVIEW、**零升級**。
`status.txt` 的 8 次寫入全部走 `write`/`edit`,`bash` **0** 次。

## 但擁有者抱怨的那件事沒有解決

原始抱怨是「還沒規劃就開始搜」。研究型 run 的前五個動作:

```
turn 1: 5 calls  [web_search × 5]
turn 2: 5 calls  [web_search × 5]
turn 3: 5 calls  [web_search × 5]
```

**這個模型一輪同時發五個工具呼叫。**
而階段閘的退場門檻是「同一條規則擋滿 4 次就讓路」——
**那 4 次全部被第一輪的並行批次一次用光。**

閘確實響了,理由也確實指出了下一步:

> C.A.S.E. 階段閘(CLAIM):這個佇列有 PENDING 任務,還沒有人認領。**問題不是搜尋** ——
> 搜幾次都可以,而且認領之後研究工具全開。問題是還沒認領就開工。
> 先用 `write` 把該任務的 status.txt 改成 IN_PROGRESS,一次寫入的事。

**但模型是在收到任何一則拒絕之前,就已經決定並送出了那一輪的五個呼叫。**
退場機制是為了「不要讓模型撞死在同一道牆上」而設計的,它假設呼叫是一個一個來的。

**門檻的單位錯了:它數的是拒絕次數,而該數的是「模型有機會看到拒絕的輪數」。**
這與 2026-08-06 的教訓同型 —— 當時是「退場門檻定 2 次,而認領只要一次寫入,吸收兩次比照做便宜」。
**兩次都是門檻定在錯的單位上。**

## 第二個缺陷:沒有交付物也能被祝福為完成

基準線 run 2 只注入兩次:認領 → **終端**。任務包裡有 `planning.md`、`retro.md`,**沒有 `output.md`**。

`nextStep()` 在 `status = REVIEW` 且 `retro.md` 存在時直接判終端,**從不回頭檢查 `output.md`**。
狀態轉換守衛也不管:`IN_PROGRESS → REVIEW` 是合法轉換。

所以一個任務可以跳過交付物、被推進器告知「交給另一個 session 核可」。
**這正是本 repo 反覆遇到的形狀:流程走完了,東西沒有產出。**

## 儀器:三個假零,最後一個由前一個修好之後才露出來

`--self-check` 先跑,不通過就拒絕量測。四種破壞、四次紅
(只認 `write`、把 `cat` 算成寫入、近似的 `customType`、不拆信封)。
前兩種是 2026-08-06 真實犯過、且會讓主指標反過來的錯。

**但自證第一次是綠的,而儀器是壞的。** 三個假零依序出現:

1. **信封** —— 記錄是 `{"type":"message","message":{...}}`,我讀了頂層的 `role`。
   第一次真實 run 回報全部 0,而 session 檔有 11 KB。
   **自證沒抓到,因為那份 fixture 是我憑記憶寫的** —— 它跟我的解析器一致,不是跟 Pi 一致。
2. **`custom_message` 沒有 `role` 欄位** —— 兩個注入計數器在結構上不可能回傳 0 以外的值。
   驗證方式不是再寫 fixture,而是拿**已保存、已知含一次注入**的真實 session 去跑,得到 `1`。
3. **fixture 不是 C.A.S.E. 專案** —— 這一個最貴。
   `isCaseProject()` 要求 `CASE.md` 或 `00_Constitution`,而我手工建的 fixture 只有 `02_Task_Queue/`。
   推進器在 `index.ts:191` 就 return,三次 run 都是 0 注入。
   **而階段閘照樣響了**(它只看佇列目錄)—— 一個守衛說話、另一個沉默,
   讀起來像 bridge 缺陷,實際是 fixture 缺陷。

**三個都是「fixture 編造 payload」的同一類。** 現在 fixture 由 `bootstrap.py` 產生,
而且腳本會**斷言自己的前置條件**:不是 C.A.S.E. 專案就中止,不再產出一頁沒有意義的 0。

## 判定

**`enableCaseAdvancer` 維持 `false`,但理由與上次完全不同。**

上次是「機制不成立」。這次是**機制成立了**(4/4 到 REVIEW、零升級、status 全走工具),
而**兩個門檻定在錯的單位上**:

1. 階段閘的退場數的是拒絕次數,而模型一輪並行五個,一輪就用光。
2. `nextStep()` 的終端判定不回頭看交付物。

**先修這兩個,再談預設值。** 打開一個會在第一輪就被穿過、又可能祝福空任務的機制,
是把一個有反應沒有結果的東西變成預設 —— 那正是本 repo 一整天在拆的東西。

## 重現

```bash
python scripts/measure-advancer.py --self-check        # 先證明計數器會紅
# pi-config/harness-config.json: enableCaseAdvancer = true
python scripts/setup.py --mode restore
mv 02_Task_Queue <repo 之外>                            # 移出,不是改名
python scripts/measure-advancer.py --runs 3 --prompt baseline --out baseline.json
python scripts/measure-advancer.py --runs 1 --prompt research --limit 1200 --out research.json
# 量完:git checkout pi-config/harness-config.json、佇列移回、restore、git status 應乾淨
```
