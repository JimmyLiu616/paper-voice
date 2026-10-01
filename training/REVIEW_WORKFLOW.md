# 從草稿到可審查的訓練資料

啟動紙聲通後，開啟 <http://127.0.0.1:8765/static/training-review.html>。

目前提供 12 份 AI 原創虛構通知、36 題問答，分為 8 份訓練草稿及 4 份開發草稿；尚無最終測試集。這是第一批核對素材，不是完整訓練集，也沒有宣稱人工標註完成。官方公開公文仍只作既有開發測試，不混入這批資料。

## 核對與匯出

1. 填寫核對者姓名或代號，選一份通知。
2. 對照固定原文，修改期限、應備文件、金額、例外條件，以及每題答案與引文。沒有提供的欄位留空；不能從文件回答的題目取消「文件有明確答案」，並確認拒答文字。
3. 日期、否定、不同身分費率、擇一／全部文件、送達／郵戳條件均需人工判斷。引文存在並不代表答案正確；若原文有歧義，寫入備註並暫不確認。
4. 自行逐份核對內容及使用授權後，勾選兩項聲明，再按「確認這份標註」。程式記錄核對者及時間，不能證明核對者身分或實際完成語意審查。
5. 「匯出已確認資料」只包含已確認的文件；「匯出全部草稿」保留未確認狀態。兩者都提供 JSONL 內容預覽及複製入口。內建瀏覽器的自動檔案下載尚未驗證成功；若沒有下載檔案，複製預覽內容並另存為 UTF-8 `.jsonl`。

修改標註或備註會撤銷該份確認，須重新核對。更換核對者姓名不會改寫先前文件記錄的核對者。沒有一鍵全數確認，也不會因為匯出而啟動訓練或上傳。

暫存只在目前瀏覽器的 localStorage，草稿檔案雜湊改變時會切換暫存版本。清除瀏覽器資料、切換瀏覽器或更換草稿版本，都可能看不到先前修改；完成後務必匯出備份。目前未提供 JSONL 匯入還原介面。正式審核資料建議存到 `training/data/`，該目錄排除 Git 與提交 ZIP。

## 微調前檢查

在專案根目錄執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\validate_training_data.py training\data\paper-voice-reviewed.jsonl
```

檢查器會拒絕未確認資料、錯誤引文、跨組重複來源及已知評測來源。只傳一份部分資料，無法證明整個 train／dev／test 分組沒有重複；要檢查完整實驗必須同時提供三組。檢查通過也不是語意正確、授權有效或模板獨立的證明。不得自行把草稿的布林值改成 true 來替代審核。

既有 UI 匯出草稿已送入 Python 檢查器驗證：12 筆皆被人工審核／授權門檻拒絕，沒有其他結構錯誤。可重現的單元測試：

```powershell
node --test tests\training-review.test.cjs
.\.venv\Scripts\python.exe -m pytest tests\test_training_data.py -q
```

下一階段需要確認過的獨立 train／dev 資料，以及未用來調參的 test 來源，再比較相同輸入下的原模型與 adapter。這批 UI 草稿尚未進入訓練；已完成的一步 QLoRA 硬體可行性實驗另見 `LORA_SMOKE.md`，不能當作公文任務改善。

## 轉成微調輸入

`scripts/prepare_training_messages.py` 已提供正式轉換入口。除了上述檢查，還要求每份資料包含 `review.reviewer`、帶時區的 `review.reviewed_at` 與 `review.method`；核對頁的已確認匯出會保留這些聲明。外部人工標註可提供同樣欄位，但聲明不能代替實際審查。轉換必須同時提供 train、dev、test 三組，以檢查跨組來源；目前 12 份草稿沒有 test，不能直接通過。

```powershell
# 僅檢查，不寫檔、不訓練
.\.venv\Scripts\python.exe -X utf8 scripts\prepare_training_messages.py training\data\train.jsonl training\data\dev.jsonl training\data\test.jsonl --name notices-001 --check-only
# 檢查成功後，移除 --check-only 產生本機輸入包
.\.venv\Scripts\python.exe -X utf8 scripts\prepare_training_messages.py training\data\train.jsonl training\data\dev.jsonl training\data\test.jsonl --name notices-001
```

輸出位於 `.runtime/prepared-training/notices-001/`，同名目錄不會覆寫。`train.jsonl` 與 `dev.jsonl` 每份文件各產生一筆四欄位擷取，以及每題各一筆問答；一份文件的不同任務維持同一 split。每筆保留來源、家族、授權、核對聲明與文件雜湊。`manifest.json` 記錄提示詞、來源／输入／輸出雜湊、各組筆數及轉換程式版本。manifest 寫入前若中斷，該目錄不能當作完整輸入包。

test 只參與分組及重複來源檢查，其原文與答案不會寫入輸入包，仍保留在原本的人工標註檔案。程式也排除已知評測來源和硬體 smoke 通知；這不是能辨識所有改寫或模板相似的語意去重器。

格式 `paper-voice-text-experiment-v1` 是獨立文字理解實驗：四個欄位皆為字串，問答包含 answer／found／evidence。它不是目前 `app.py` 完整輸出的替代品，未接到正式服務。合成單元測試中的假核對者只存在隔離測試資料，不能算正式人工審核。

## 實際 tokenizer 長度與 loss mask

2026-10-01 使用固定 revision 的 Ministral tokenizer 離線讀取原始草稿；12 份文件形成 48 組欄位／問答輸入，長度 261–421 tokens，在本輪 1024 上限內全部通過，沒有截斷。`test` 模式的提示詞 token prefix 與 `finetuning` 模式完整對話前綴相同；提示詞的 labels 皆為 -100，僅 assistant 回答及 EOS 計入 loss。

```powershell
.\.venv-train\Scripts\python.exe -X utf8 scripts\inspect_training_tokens.py --max-tokens 1024
```

報告 `tokenization-validation.json` 保存每組長度、模型 revision、tokenizer 設定雜湊檢查及程式雜湊。共用格式化函式與正式轉換器一致；本工具沒有繞過正式轉換器產生訓練檔，不儲存 token dataset、不載入模型權重、不執行 optimizer，也未修改人工審核狀態。

正式人工修改後的資料必須重新檢查長度與 mask，不能沿用這份草稿報告。`training_tokens.py` 提供可重用的遮罩檢查函式，前綴不符、缺少答案／EOS、超長或多輪對話均拒絕。這批 421-token 以內序列的實際訓練顯存尚未驗證；先前 109-token smoke 的顯存結果不能直接外推。48 組格式檢查通過不代表語意正確或已具備正式訓練資料。
