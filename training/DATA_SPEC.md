# 生活通知／公文理解資料

**2026-10-02更新：** 本機核對頁已有12份逐份確認聲明，已保存原始匯出並固定8 train／2 dev／2 test，完成首次32任務LoRA與新程序重載。候選新增否定題拒答，未採用；test未推論。詳見 [REVIEWED_RUN_001.md](REVIEWED_RUN_001.md)。公開隨附草稿仍保持未確認，以下「未核對／待訓練」記述為較早流程或公開草稿狀態，不能用來描述本機這次實驗。

第一批 12 份原創虛構通知／36 題草稿可在 [本機核對頁](http://127.0.0.1:8765/static/training-review.html) 編輯與逐份確認；操作、匯出與限制見 [REVIEW_WORKFLOW.md](REVIEW_WORKFLOW.md)。目前均未經人工確認，尚無最終測試資料。

本輪優先研究期限、應備文件、費用與例外條件。這份格式供文字理解 LoRA 候選實驗；v5 標準文字開發檢查雖曾全通過，後續保留案例與語意核對實驗仍發現事件、否定與對象錯誤，因此需同時準備文字理解正反例與實拍圖文對。圖片 OCR 微調另需授權圖片與逐字稿；目前沒有經人工複核、可用來驗證任務改善的訓練集。

建議首批收集 40 個不同來源／模板的文件家族，先用 24／8／8 家族分為 train／dev／test；這只是起始研究規模，不代表足夠證明泛化。每份文件標 4 個重點欄位與 2–4 個問題，包含不能從文件回答的問題。相同文件的清晰照、歪斜照、裁切、改日期版留在同一組。現有 evaluation 文件已用作開發或保留評估，不作本輪訓練資料。

一行一個 JSON，存於 `training/data/*.jsonl`，原始資料預設排除 Git 及提交 ZIP。使用下列格式；這個範例只是格式示意，沒有宣稱人工核對完成。

```json
{"schema":"paper-voice-understanding-v1","source_id":"original-notice-001","family":"equipment-return","split":"train","license":"MIT","rights_confirmed":false,"human_reviewed":false,"document":"歸還期限：2027年4月20日，以櫃台簽收為準。\n應備文件：借用收據。\n費用：免費。\n已歸還者無須再辦理。","fields":{"deadline":"2027年4月20日，以櫃台簽收為準。","required_documents":"借用收據。","amount":"免費。","conditions":"已歸還者無須再辦理。"},"questions":[{"question":"最晚何時歸還？","answer":"2027年4月20日，以櫃台簽收為準。","found":true,"evidence":["歸還期限：2027年4月20日，以櫃台簽收為準。"]},{"question":"承辦人姓名是什麼？","answer":"文件沒有提供。","found":false,"evidence":[]}]}
```

人工複核時特別確認：

- **期限**：區別公告日、活動日、截止日；保留郵戳／送達條件；起算日未知就不能標確切日期。
- **應備文件**：完整清單、正本／影本、擇一／全部、不同身分的要求；費用與資格不能混入文件清單。
- **費用**：金額、幣別、每人／每件、免費／退費與資格條件。未提到費用不代表免費。
- **例外**：已完成免辦、取消、禁止、特殊資格，不省略否定詞。
- **問答**：證據必須真的回答所問角色；公告單位不等於承包廠商。`found=true` 表示有依據，禁止事項也可有依據。

執行 `python scripts/validate_training_data.py training/data/train.jsonl training/data/dev.jsonl training/data/test.jsonl`。檢查器拒絕未確認授權／人工複核、跨組同源、相同文字跨組及引用不存在。它不能自動證明授權、人工審核身分、語意或模板獨立性；仍要人工審核。若只輸入 train，僅檢查所提供資料，不能宣稱完成三組防洩漏。

保留測試只在候選 adapter／提示詞／評估規則凍結後執行。模型產生的標註只能當草稿，不能自動設 `human_reviewed=true`。匯出程式須讀取經檢查資料產生訓練 messages；不把使用者在網站上傳的文件自動加入訓練。

已實作 messages 轉換器 `scripts/prepare_training_messages.py`，額外要求三組資料、逐份核對者／時間／方法及唯一來源 ID。只輸出 train／dev messages，不輸出 test 內容與答案。完整指令、輸出格式與原始草稿的 tokenization 檢查見 `REVIEW_WORKFLOW.md`；人工修改後需重新檢查。實驗中的四字串欄位 schema 與正式服務不同，不可直接替換產品模型輸出。

`smoke-fixture.json` 是另外編寫的單筆虛構置物櫃通知，保留 `human_reviewed=false`，用途僅為 GPU／optimizer／adapter 儲存重載檢查，不適用上述正式訓練資料格式。它不來自公文、使用者上傳或既有評測題；不得拿其訓練 loss 或生成結果宣稱公文理解改善，也不得日後放入保留測試。該實驗由 `scripts/train_lora_smoke.py` 單獨執行，不會放寬正式資料檢查器的人工複核門檻。

四份網路公開公文已被用來觀察失敗與調整程式，因此也列入既有開發來源排除清單。檢查器會比對公開來源 ID 與 family；它不能偵測刻意改名／改寫後的所有重複來源，仍需人工檢查來源與模板家族。這些公文沒有因為能公開下載，就自動被認定可用作模型訓練。
