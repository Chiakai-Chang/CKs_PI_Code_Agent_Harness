# oh-my-pi 學習筆記：Hashline 雜湊錨定編輯系統

> 來源：`reference/oh-my-pi/docs/tools/edit.md`、`packages/hashline/src/*`、`packages/coding-agent/src/edit/*`

## 核心機制

oh-my-pi 的 `edit` 工具預設使用 **hashline patch language**，以內容雜湊而非行號定位編輯：

- `read`/`grep`/`write` 讀取檔案時，對整個歸一化文件（LF、無 BOM）計算四碼大寫十六進位雜湊標籤 `[PATH#TAG]`
- `edit` 的 patch 區塊以 `[PATH#TAG]` 開頭，操作使用 `SWAP N.=M:`、`DEL N.=M`、`INS.PRE/POST N:`
- 套用時先比對檔案當前雜湊是否等於 TAG：匹配則直接按行號套用；不匹配則啟動復原流程

## 復原機制（Recovery）

當錨定過期（stale anchor）時，系統不會丟棄編輯：

1. 從 `SnapshotStore` 取出 TAG 對應的歷史完整文件版本
2. 對該歷史版本套用編輯 → 產生 patch
3. 以 diff-match-patch 將 patch **3-way merge** 到當前檔案內容（`fuzzFactor: 0`，零容錯）
4. 成功則返回復原後結果並附警告；失敗則拒絕，要求重新 `read`

快照商店是抽象基底類別，預設實作為 LRU 快取：每條路徑保留短歷史版本鏈，讓會話內連續編輯仍能對舊版本復原。

## 樹節點區塊操作（Block Ops）

整合 tree-sitter 解析器，支援結構化操作：

- `SWAP.BLK N` / `DEL.BLK N` / `INS.BLK.POST N:` — 以 tree-sitter AST 解析行 N 開頭的完整程式碼區塊
- Markdown 段落（heading + body + 嵌套子節）也視為一個 section node
- 失敗時自動降級為行號操作，而非直接報錯

## 對本專案的啟發

### 直接可用
- **Bridge 驗證**：我們目前的 bridge/extension 註冊完全依賴 `settings.json` 路徑匹配，沒有內容驗證。可引入「內容雜湊標籤」概念：bridge 啟動時計算自身關鍵檔案的雜湊，寫入 `pi-config/manifest.json`，下次啟動比對，發現橋接程式碼被意外修改時發出警告。
- **編輯安全**：我們的 `setup.py` / `restore.py` 會覆寫設定檔。可引入 hashline 風格的「錨定確認」：在覆蓋關鍵設定前先驗證當前內容雜湊是否為預期版本，避免覆蓋使用者的有意變更。

### 概念借鑑
- **零容錯復原**：oh-my-pi 的 `fuzzFactor: 0` 設計哲學值得學習 — 寧可拒絕也不要靜默錯誤應用。本專案的設定還原腳本應遵循同樣原則。
- **快照商店抽象化**：將「版本存儲」抽象為可插拔介面，方便未來接入 SQLite 持久化。

### 改善空間（oh-my-pi 自身）
- hashline 的 Lark 語法與手動解析器並存，容忍了太多非規範輸入形狀（`SWAP N-M:`、`SWAP N..M:` 等），增加維護負擔。
- `*** Abort` 靜默終止解析不產生警告，可能讓使用者困惑為何部分 patch 未生效。
