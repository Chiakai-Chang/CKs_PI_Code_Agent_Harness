# Task_015_advancer_settled_loop — ESCALATED,並且是事先寫下的那個條件

任務包在 `02_Task_Queue/Task_015_advancer_settled_loop/`(gitignore)。

## 四項移植完成且有測試

1. **位置**:續跑改掛 `agent_settled`。探針實測:它每個 agent run **只觸發一次**,
   在 `agent_end` 之後 1ms;`turn_end` 每輪觸發 —— 那是「正常進行的步驟被判停滯」的成因。
2. **停滯判準**:加權 progress signal(write/edit 3、bash 2、read/grep/find/ls 1、其他 2),
   `=== 0` 才算空轉。權重借自 pi-until-done,已註明是借來的。
3. **失敗歸屬**:放棄時**暫停推進器自己**,訊息裡沒有 `ESCALATED`、沒有 `status.txt`。
   先前五次 run 三次 ESCALATED、至少兩次任務本身好好的 —— 那是自動化的放棄被寫成任務的失敗。
4. **終端狀態**:「交還另一個 session 核可」說一次就停,不計時、不升級。

破壞 7 種、7 種被抓到;**899 tests OK**。

## 但迴圈沒有接起來

| 嘗試 | 結果 |
|---|---|
| `sendMessage(followUp, triggerTurn:true)` | handler 有跑、步驟有算出(探針為憑),**注入從未進入 session** |
| `sendUserMessage(followUp)`(pi-until-done 用的) | **10 分鐘無 session 檔,強制中止**;`await` 疑似卡住關閉流程(已改為不 await) |

`agent_settled` 在 `agent_end` **之後**:能接收 followUp 的 agent 迴圈已經結束。
**這不是參數問題,是移植的前提在 `--print` 模式下不成立。**

## 需要的是決定,不是繼續修

1. 改掛 `agent_end`(迴圈結束前),先量它有沒有同樣問題;
2. 接受「推進器只在互動式 session 有效」,量測方式改成互動式;
3. 放棄自動續跑,只留階段閘(Task_016)+ 人類推進。

## 最該記住的一條

**位置對了不等於話送得出去。**

同一天早上,`blocked-claim` 才因為訂閱了不會觸發的事件而從未響過;
下午我把推進器搬到了正確的事件,單元全綠、探針證明時機正確 —— 然後注入一次都沒送到。
**任何新的注入點,第一個探針應該是「這裡送得出去嗎」,不是最後一個。**
