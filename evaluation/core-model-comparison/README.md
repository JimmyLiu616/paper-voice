# 核心模型替代方案比較

為降低Gemma自訂授權參賽認定尚未確認的風險，測試本機已下載且[官方模型卡標示Apache-2.0](https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512)的Ministral 3 3B。Ollama本機回報該固定digest具有vision能力；這次實際跑讀圖、擷取及問答，與較早只作語意核對的實驗不同。

## ministral-core-v1

相同5頁既有公文、20項欄位片段／留空檢查、10題問答，在隔離程序中呼叫同一FastAPI應用的ASGI介面，真正使用Windows OCR及Ollama模型。每頁交替模型先後順序；各配對Windows OCR線索完全一致。僅改隔離程序內的模型名稱，未改正式服務、提示詞、後處理或權重。

| 模型 | 欄位檢查 | 問答機械檢查 | 執行錯誤 |
|---|---|---|---|
| Gemma 3 4B Q4_K_M | 18/20 | 10/10 | 0 |
| Ministral 3 3B Q4_K_M | 15/20 | 7/10 | 0 |

**不直接替换正式模型。**Ministral在雙語表格補出核發限制，但費用卡退步；培訓公告的補助金額卡與免附文件問答退步；補助說明的期限、金額及兩題問答也退步。其中一題的answer竟為字串 `found=true`，即使附了相關引文，也不是可理解的回答。另有空白表單欄位被當成聯絡方式或行動的問題。Gemma既有錯誤同樣保留，沒有因候選退步就宣稱原模型已完全正確。

完整逐例代理審閱見 [review.json](ministral-core-v1/review.json)，機械檢查見 [paired-checks.json](ministral-core-v1/paired-checks.json)。這是已開啟開發集，不是獨立測試或一般準確率，也不是微調。未針對Ministral另調提示詞，因此只否定目前配置可直接替代，沒有推論模型不可能改善。

## 重現與資料範圍

先依 `evaluation/public-documents/README.md` 準備同一批本機文件及其manifest，安裝並核對兩個模型digest，再執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\compare_core_models.py --name ministral-core-v1
```

同名目錄不覆寫；如已跑過，使用新的run名稱。完整原始輸出在 `.runtime/core-model-comparison/<name>/`，不自動公開。公開資料夾僅包含模型／程式雜湊、檢查結果、審閱及程式快照；沒有官方原始PDF、圖片或完整轉寫。快照只供版本追溯，直接執行請用專案 `scripts/` 入口。

時間為每頁單次观察，受冷載入、模型切換和快取影響，不作一般速度比較。程式快照沿用正式介面的Gemma文字標籤，隔離候選的實際模型以metadata與結果model欄位為準。正式網站仍使用Gemma，主辦的授權認定問題尚未因此解決。
