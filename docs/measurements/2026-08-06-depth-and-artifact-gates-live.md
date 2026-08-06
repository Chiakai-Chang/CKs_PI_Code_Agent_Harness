# 深度閘與產出閘:第一次實測開火

**日期**: 2026-08-06
**先前狀態**: 兩個閘寫好後,單元測試 11 條全綠、刻意破壞三次全紅、安裝副本一致 ——
**實測 0 次開火**,被我記為「探針結構上驗不到」。

**那句話只對那支探針成立。** `measure-triggers.py` 的情境跑在乾淨暫存目錄、而且都是第 3 次
搜尋就開頁的形狀,所以永遠到不了「9 次搜尋 0 開頁」的條件。換一個會自然產生該條件的情境即可。

---

## 方法

fixture:全新暫存目錄 + `git init`,無 CASE 骨架、無既有 plan。

請求(**沒有暗示模型別開頁,那是製造結果**):

> 我要一份速查表:列出這 15 個工具各自的最新穩定版本號 —— Node.js、Python、Go、Rust、
> Deno、Bun、TypeScript、Vite、PostgreSQL、Redis、Docker、Kubernetes、Nginx、Terraform、
> Ansible。只要版本號,不用細節說明。

十五個各自用搜尋摘要就能回答的事實 —— 這是「廣度無深度」的自然形狀,不是誘導。

## 結果

```
web_search 17 · web_open 6 · write 1
Depth guard    x3
Artifact guard x2
Citation guard x0
```

呼叫序列與擋阻位置:

```
 #1– #8   web_search                       (opens = 0)
 #9       web_search  → Depth guard 擋      ← 門檻:searches > 8 且 opens == 0
 #10–#12  web_search  → 再擋 2 次(退場預算 3 次用完)
 #13–#15  web_open ×3                       ← 模型照做
 #16–#17  web_search  → Artifact guard 擋 ×2 ← 門檻:searches > 12 且 writes == 0
 #18      write                              ← 模型照做
 #19–#24  web_search / web_open 交錯
```

工作目錄留下 `findings.md`,1,257 字元,含 **11 處 `http`**。

## 三個閘各自做對了自己的事

| 閘 | 條件 | 實際 | 模型反應 |
|---|---|---|---|
| 深度 | 9 次搜尋且 0 開頁 | 在第 9 次呼叫開火,分毫不差 | 開了 3 頁 |
| 產出 | 13 次搜尋且 0 寫檔 | 開火 2 次 | 寫出 `findings.md` |
| 引用 | ≥800 字元且 0 網址 | **正確保持沉默** | —— 檔案本來就有 11 個網址 |

**這是「擋下之後模型真的改變行為」的第一份直接證據。** 先前所有實測只證明過引用閘會開火
(檔案內網址 0 → 10/15),沒有證明過模型會照著擋阻理由做下一步。

## 退場機制也一併驗到

深度閘擋滿 3 次即退場(`MAX_BLOCKS_PER_GATE`),序列顯示第 10–12 次呼叫仍是搜尋 ——
也就是模型在前兩次擋阻後沒有立刻照做,第三次之後閘退場,而模型**在退場之後才開頁**。

這說明兩件事:
1. 退場機制沒有讓 session 卡死(設計目的達成)
2. 行為改變發生在第 3 次擋阻之後,不是第 1 次 —— **一次擋阻不夠**,這個預算不是多餘的

## 這條記錄的真正價值不在數字

我曾把這兩個閘記為「探針結構上不可驗證」,並據此把驗證責任推給使用者。使用者質疑之後,
建一個合適的 fixture 只花了二十分鐘。

同一次方法(真實 fixture + 實跑)在 C.A.S.E. 守衛上找出三個真缺陷,其中一個是
`bash` 可以繞過只掛在 `write`/`edit` 的目錄圍堵守衛。

> **「這個測不了」要先枚舉過才能說。** 探針是一支儀器,不是能力的邊界。

## 重現

```bash
D=$(mktemp -d) && cd "$D" && git init -q
pi --print --session-dir "$D/.sess" "我要一份速查表:列出這 15 個工具各自的最新穩定版本號 —— \
Node.js、Python、Go、Rust、Deno、Bun、TypeScript、Vite、PostgreSQL、Redis、Docker、\
Kubernetes、Nginx、Terraform、Ansible。只要版本號,不用細節說明。"
grep -o "Depth guard\|Artifact guard" "$D"/.sess/**/*.jsonl | sort | uniq -c
ls "$D"
```

本機模型 temperature 0.6,單次樣本。**這是存在性證據(這兩個閘會在真實情境開火並改變行為),
不是頻率證據。**
