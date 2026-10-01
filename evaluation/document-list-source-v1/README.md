# 取回被清單改寫擋下的應備文件段落

2026-10-02。public-v12就學補助第2頁的模型輸出「申請書、申請應備文件」不在原文中連續出現，因此被舊驗證器隱藏。它的 evidence 實際對應「應填寫申請書並備妥申請應備文件」及郵寄指示；本輪測試能否保留這段已有來源的資訊。

候選只處理 required_documents 引用未通過的清單格式。至少兩項以頓號或換行分隔、符合文件名稱形式的項目，必須逐項逐字、依序、不重複使用同一位置對應 evidence；evidence 又必須位於唯一原文段落，並明示應／須／需／請填寫、備妥或檢附等要求。成立才複製完整原文段落作為 value 及 evidence。新增文件、改名、倒序、無原文依據、僅為附件／參考資訊或豁免，不經此入口恢復。

這不補出原文沒有列出的文件，也不把「申請應備文件」這個概稱當成完整清單。恢復段落保留紙本申請、郵寄方式等上下文，可能比一般文件清單長；來源存在不等於OCR或欄位語意完全正確。

## 固定輸出比較

以public-v12五份真實模型擷取輸出重播，舊版35欄與保存紀錄一致；候選只有就學補助第2頁的 required_documents 改變，其餘34欄相同。20項片段／留空檢查19→20，見 `public-v12-replay.json`。這是同一份輸出的來源格式修正，不是新圖片推論或一般準確率。

13項合成測試涵蓋改名、加文件、順序顛倒、重複利用同一來源、費用混入、附件與豁免、來源錯字／歧義、全形數字與既有有效引用。完整164項Python測試通過，保留1項既有Starlette/httpx棄用警告。

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_document_list_source.py -q
.\.venv\Scripts\python.exe -X utf8 scripts\replay_document_list_source.py --run public-v12
.\.venv\Scripts\python.exe -X utf8 scripts\evaluate_public_documents.py --name 新的英數名稱 --isolated
```

重播需要本機保存的 `.runtime/public-documents/runs/<run>/` 原始輸出與 `.runtime/document-list-source-v1/baseline-app.py`，不覆寫同名報告。官方文件全文不隨公開包發布；公開報告保存雜湊、分項判定與變更範圍。沒有變更模型權重、提示詞或問答驗證，也沒有執行微調或保留test推論。

## 圖片回歸與採用

public-v13完成5頁、20/20欄位片段／留空檢查、10/10問答檢查、0執行錯誤。五頁逐字稿與public-v12相同；新生成經同批重播為舊版19/20、新版20/20，仍只有申請書欄恢復，其他34欄一致。已將本機服務更新至同一受測app SHA256。

一題期限答案僅有換行差異，日期與郵戳規定保留；新引文未包含後面的逾期不受理句子。地點／行動錯誤、清單完整性及上一輪費用短答限制仍在。20/20只代表已列出的四類欄位片段檢查，不能說所有欄位或語意全對；評測已用於開發，亦非未見測試。完整審閱見 `../public-documents/public-v13-review.json`。
