# cua 審視 —— 我們沒有沙箱,而且「沙箱」有兩種

**日期:2026-08-10**
**來源:** https://github.com/trycua/cua(擁有者提供)
**起因:** 目錄圍堵守衛被繞過六次,每次修完下一次換一種方式。
擁有者的批評:「你只是修補左邊漏右邊,應該有大局觀、宏觀再到微觀」。**這個批評是對的。**

---

## 0. Provenance

* 出貨中的產品(cua.ai),不是提案。文件在 `docs/content/docs/`,分
  concepts / how-to-guides / reference / tutorials 四層
* 讀的是 `concepts/how-sandboxes-work.mdx` 與 `concepts/how-permission-policies-work.mdx` ——
  依審視程序第 (2) 條,只讀離我們當前問題最近的兩份

## 1. 先澄清:我們從來沒有沙箱

擁有者問「什麼時候有沙箱設計了?」—— **沒有過。**
這個 harness 唯一的檔案系統邊界是 `bash-containment.ts`,一個**解析字串的守衛**。

而「沙箱」在這個脈絡下是兩種完全不同的東西:

| | 是什麼 | 對我們適不適用 |
|---|---|---|
| **cua 的沙箱** | 整台隔離的機器(VM / 容器),自己的檔案系統與 OS 狀態 | **不適用** —— `pi` 要改的就是使用者自己的專案;整台隔離等於什麼都不能做 |
| **cua 的權限引擎** | 每次工具呼叫前的統一授權點,**deny-by-default** | **適用,而且正好指出我們錯在哪** |

## 2. Pi 自己怎麼看這件事

安裝版 `dist/bun/restore-sandbox-env.d.ts` 的註解逐字寫著:

> Bun compiled binaries have an empty `process.env` when running inside
> **sandbox environments (e.g. nono on Linux/macOS)**

**Pi 不提供沙箱,它只是「能在沙箱裡跑」,並為此補救環境變數。**
也就是說 Pi 的作者預期邊界在**外面**,由使用者用 nono / 容器之類的東西提供。
我們把邊界做在 bash 字串解析裡,從一開始就是把它放錯層。

`grep -i "sandbox\|permission\|allowlist"` 整個 `extensions/types.d.ts`:
只有 `ui.confirm`。**擴充層沒有任何權限機制可用。**

## 3. 唯一真正可移植的一句話

cua 的權限引擎:

> The engine is **deny-by-default**. A tool that is not explicitly mentioned in
> the policy is blocked.
>
> If the path is missing, unreadable, empty, or invalid, **runtime construction
> fails** before tools are registered or a service binds its action endpoint.

我們的圍堵守衛,它自己的檔頭:

> …and **fails open on everything it cannot parse**.

**兩個是相反的預設,而六次繞過每一次走的都是「看不懂所以放行」那條路。**

`fails open` 當初的理由是真的(誤擋會讓守衛被關掉,而關掉的守衛什麼都不保護)。
問題不在這個理由,在**它把哪一邊放在無界那一側**:

* 現況:枚舉「會寫檔的形式」→ **無界** → 永遠有第 N+1 種
* 反過來:枚舉「已知唯讀的指令」→ **有界** → `ls` `cat` `grep` `find` `head` `wc` `git log` … 列得完

**這不是把 fail-open 換成 fail-closed,是把無界的那一半換到白名單去。**

## 4. 明確不採用的

| 項目 | 決定 | 觸發條件 |
|---|---|---|
| VM / 容器沙箱(lume、kasm) | **不採用** | 使用者要 agent 改自己的專案。若哪天要跑「不受信任的任務」,這是正確答案 |
| Rego / YAML 政策檔 | **不採用** | 我們只有一個邊界要守;政策語言是給多租戶用的 |
| managed + user 雙層政策 | **不採用** | 同上,單機單使用者 |
| **deny-by-default 的極性** | **採用** | 就是下一步 |
| **統一授權點**(所有路徑都經過同一個判斷) | **待評估** | 我們有四個守衛各自判斷,而 Round 12 已經量到它們互相搶話 |

## 5. 我自己的錯,寫下來

`CLAUDE.md` 的 Prior Art First 寫著「設計任何新機制前,先開 REGISTER.md 找同樣的能力」。

**圍堵守衛改了六輪,我一次都沒有回頭查。** 每一輪都是:出事 → 修 → 出事 → 修。
而這件事有標準答案,且 Pi 自己的檔案裡就寫著它預期外部沙箱。

**教訓不是「要查 prior art」—— 那條規則早就在了。是:**
**當同一個地方修到第三次,那不是缺陷,是設計錯了,而繼續修會讓它看起來像在進步。**

## 6. 下一步(尚未實作)

把 bash 圍堵從「枚舉寫入形式」反轉成「枚舉唯讀指令」:

* 指令不在唯讀白名單裡、且命令中出現專案外的絕對路徑 → 拒絕
* **不需要知道它會不會寫**,這正是無界的那一半
* 白名單保持短且封閉,新增要有理由

**必須先寫下失敗條件:** 這個反轉會製造誤擋(第一批就是 `python3 D:/other/tool.py` 這種
合法的外部執行)。若真實 run 出現誤擋且使用者必須關掉守衛,**這個設計就輸了**,
而不是再加一條例外。
