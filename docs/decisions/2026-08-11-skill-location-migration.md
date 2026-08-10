# 技能註冊位置遷移 —— 設計(尚未實作)

**日期:2026-08-11**
**等級:L1**(改變安裝行為,影響新裝 / 更新 / 重裝 / 解除安裝)
**狀態:設計待核可。一行程式碼都還沒改。**

---

## 1. 起因:harness 是自己主要失效模式的成因

五個真實 run 裡有四個「跑錯專案」—— 模型在 harness 的安裝目錄裡工作,
而不是自己的 cwd。七輪守衛修正沒有改變這個數字。

**量測(2026-08-11,`PI_HARNESS_DUMP_PROMPT` dump 真實系統提示):**

```
系統提示總長          41,875 字元
"CKs_PI_Code_Agent_Harness" 出現   28 次
工作目錄字串出現                    1 次
<location> 標籤        45 個 → 23 個指向 D: 的 harness repo
                             22 個指向 C:\Users\User\.agents\skills
```

**28 比 1。** 模型過去一看,那裡有 git repo、有 `02_Task_Queue`、有 docs ——
它認定那才是專案。**這是推論,不是混淆**(見 MECE Round 13)。

沒有 harness 的使用者不會有這個問題。**這 23 個路徑是 harness 自己放進去的。**

## 2. 那 23 個從哪來(查證,非推測)

| 來源 | 數量 | 機制 |
|---|---|---|
| `pi-skills/` | 3 | 直接寫進 `~/.pi/agent/settings.json` 的 `skills` 陣列 |
| `external/` 子模組 | 20 | 寫進 `pi-config/external-skills-manifest.json`,由 `skill-namespace-guard` 在 `session_start` 動態註冊 |

兩條路都用 **repo 的絕對路徑**。

而另外 22 個之所以顯示 C:,是因為它們住在 `~/.agents/skills/`(使用者自己的收藏,62 個),
以及 `~/.pi/agent/skills/`(16 個 junction)。**Pi 顯示的是它拿到的路徑。**

## 3. 決定性實驗(已做)

問題:**如果改用連結指向中性位置,Pi 會顯示連結路徑還是解析後的真實路徑?**
若它解析,整個方案不成立。

做法:在 `~/.pi/agent/skills/` 建一個 junction 指向 repo 裡**尚未註冊**的技能,
dump 系統提示。

```
mklink /J probe-adversary D:\...\pi-skills\core\adversary-review

技能總數:45 → 46
location:C:\Users\User\.pi\agent\skills\probe-adversary\SKILL.md
```

**Pi 顯示連結路徑。** 探針已移除,環境復原。

(第一次探針用了**已註冊**的 `graphify`,結果只出現一個 D: location ——
那無法區分「解析了連結」與「同名去重」。換成未註冊的技能才是有意義的實驗。)

## 4. 設計

**把 repo 的技能改成:在 `~/.pi/agent/skills/<name>` 建立連結指向 repo,
並停止用 repo 絕對路徑註冊。**

* **連結而非複本** —— 編輯 repo 立即生效,不需要重跑 restore。複本會製造
  「我改了但沒生效」這一整類問題,而本 repo 已有一條同型的疤
  (`installed-copies-drift-silently`)
* Windows 用 junction(`mklink /J`,不需管理員權限);POSIX 用 symlink
* `<location>` 因此顯示 `~/.pi/agent/skills/...`,harness 路徑從提示裡消失

### 一致性:三種情境都必須產生相同結果

| 情境 | 現況 | 遷移後 |
|---|---|---|
| **新裝** | 寫 settings + manifest,都是 repo 路徑 | 建連結;settings 與 manifest 改指連結路徑 |
| **更新**(repo 有新技能 / 改名 / 移除) | 重寫 settings + manifest | **以 repo 為唯一真相重建連結**:多的刪、少的建、指錯的重指 |
| **重裝** | 覆寫 | 同「更新」——**冪等** |
| **解除安裝** | 移除 settings 條目 | **只移除本 harness 建立的連結**,絕不碰使用者自己的技能 |

### 「只移除自己建立的」怎麼保證

**不能靠名字猜。** `~/.pi/agent/skills/` 裡已經有 16 個 junction 指向
`~/.agents/skills/`(使用者的),而未來會有 harness 的。兩者混在同一個目錄。

**判定規則(可機械判定,不靠清單記憶):**
一個連結屬於本 harness,**當且僅當它的目標解析後落在 repo 之內**。

* 這條規則對**新裝、更新、重裝**都成立,不需要維護額外狀態
* 使用者自己的連結指向 `~/.agents/...`,永遠不會被誤判
* repo 換位置之後舊連結會變成 dangling —— 那也解析不到 repo 內,
  所以需要**第二條規則**:dangling 且指向任何含 `CKs_PI_Code_Agent_Harness`
  的路徑,也算本 harness 的,可清除

### 明確不做的

* **不動 `~/.agents/skills/`** —— 那是使用者的收藏(62 個),不是我們的地盤
* **不改技能內容或名稱** —— 這次只動註冊位置
* **不刪除任何非連結的目錄** —— 若 `~/.pi/agent/skills/<name>` 是真實目錄而非連結,
  一律不碰並記錄警告。使用者可能手動放了東西

## 5. 風險與先寫下的失敗條件

| 風險 | 應對 | 失敗條件 |
|---|---|---|
| 名稱衝突(harness 技能與使用者技能同名) | `skill-namespace-guard` 已在做碰撞偵測 | 若遷移後衝突數上升,回退 |
| junction 在某些檔案系統不支援 | 失敗時回退為「照舊用 repo 路徑註冊」並記錄 | 靜默失敗 = 不可接受 |
| 連結指向的 repo 在 SD 卡上,卡拔掉就 dangling | 已知;`verify-bridges.py` 之類的檢查要能報 | 若 dangling 造成 Pi 啟動失敗而非降級,回退 |
| **Pi 未來版本改成解析連結** | 提示裡 harness 路徑會回來 | **量測方式已固定**:dump 提示、數 harness 出現次數。這是可持續驗證的 |

**成功判準(在跑任何模型之前就能量):**
遷移後 dump 系統提示,`CKs_PI_Code_Agent_Harness` 出現次數應從 **28 降到個位數**
(剩下的是 bridge 路徑等非技能來源)。**沒有降下來就是設計失敗,不是調參數。**

**行為判準(需要模型):** 之後跑 T2 三輪,量認領位置。
**但那是第二步 —— 第一步的成敗不依賴模型。**

## 6. 實作順序

1. 寫一個**冪等的連結同步器**:以 repo 為真相,建/刪/重指
2. `restore.py` 改成呼叫它,並把 settings 與 manifest 改指連結路徑
3. `uninstall.py` 改成用「目標落在 repo 內」規則清除
4. 測試:新裝 / 更新(新增、改名、移除技能)/ 重裝(冪等)/ 解除安裝 / 使用者技能不受影響
5. **dump 提示,量 28 → ?**
6. 只有在 5 通過之後,才跑 T2

---

## 相關

* [MECE Round 13:把導航問題當成資安問題](../mece/rounds/2026-08-10_round13_把導航問題當成資安問題.md)
* [cua 審視:我們從來沒有沙箱](../prior-art/2026-08-10-cua-review.md)
* [PROGRESS.md](../../PROGRESS.md) —— L1 對齊是這一項服務的目標層
