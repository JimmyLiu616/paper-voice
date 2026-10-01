# v13：空白聯絡方式與回答格式檢查

2026-10-02。正式候選只保留兩項狹窄檢查：隱藏電話空白底線，並拒絕空白或純 `found=true` 等結構旗標回答。前者標為待核對，後者HTTP502提示重新提問，不宣稱文件沒有資料。模型、權重及提示詞不變。

原本同時攔截公報篇名作地點的候選，雖三笔固定輸出重播通過，圖片問答卻從10/10退步為9/10，已撤回。這項已知地點錯誤仍待處理；見 `../output-format-v1/`，不能宣稱三類問題全數修復。

`report.json`從未部署的Ministral比較實驗中重播兩筆保存輸出，2/2攔截成功。這不是目前Gemma新增成功辨識數，也不是模型準確率。新增11項測試含真實錯誤的最小案例、合法電話與信箱及正常回答；完整Python回歸108項通過（1項既有棄用警告）。正式Gemma圖片流程另見 `../public-documents/public-v10-summary.json`。

重播命令：`python scripts/replay_output_formats.py`。需保有本機 `.runtime/core-model-comparison/ministral-core-v1/results.jsonl`，輸出目錄已存在時停止，不覆寫報告。公開包不含完整逐字稿；可獨立執行 `python -m pytest tests/test_output_format.py` 驗證最小案例。

完整Gemma圖片回歸public-v10：欄位16/20、問答10/10、0執行錯誤。前4頁逐字稿／欄位／問答與public-v8完全一致；最後一頁逐字稿不同，期限及費用因原文引用檢查而留空。這次分數低於較早18/20，不能宣稱整體改善。

追加單頁診斷：以public-v10最後一頁逐字稿生成一次新擷取，讓v12與本版驗證函式共用同一份模型輸出；所有7欄結果一致，見 `paired-validation.json`。`scripts/check_format_validation.py`亦比對共用解析函式與模型提示詞AST未變。這只隔離該次輸出的驗證器差異，不足以證明完整圖片流程沒有任何波動或退步；原16/20分數保留。
