# 待辦事項的來源段落與跨行條件

2026-10-02。public-v13四類欄位檢查已20/20，但它沒有評分 action。檢查實際輸出仍發現兩項使用問題：就學補助把「提出申請補助時仍未就業」當待辦；代辦表格只顯示「者，請填委託書……」，漏掉前一行的適用條件。

原因在程式來源選擇：舊規則把「申請補助」中的「請補」當指令，且只支援沒有編號、同一行有內容的「申請方式」。新的選擇會優先保留唯一明示辦理方式的完整段落，包含編號子項；不把「申請」裡的「請」當祈使動詞。對「者，請……」跨行片段，只有前一行以明確主語加如／若條件開始且尚未結束時才接回，不猜測缺失前文。

第一版同一輸出重播只修好1/2案例：網址的冒號被誤認新標題，截掉紙本申請。追加URI行的邊界處理後2/2通過；僅在辦理方式段落啟用，其他欄位解析維持原行為。原文中的斷行網址、OCR錯字不自動改寫。

## 分開計分的證據

- `public-v13-replay.json`：第一候選1/2，保留失敗紀錄。
- `public-v13-uri-lines-replay.json`：同一批實際模型擷取輸出，兩項待辦診斷0→2/2，只變更兩個action，其餘33欄相同。原本四類欄位仍20/20，不把分母改成22來包裝。
- `checks.json`：兩項已知開發失敗的必要片段與排除片段，由Codex依既有原文編寫，不是獨立人工語意評測。
- 32份已開啟的合成回歸紀錄，以最終服務欄位重建輸入，比較新舊驗證器，無欄位差異；這不是原始模型生成重播或重新讀圖，見 `synthetic-replay.json`。
- 新增13項合成程式測試，完整177項Python通過；有1項既有Starlette/httpx棄用警告。

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_action_source.py -q
.\.venv\Scripts\python.exe -X utf8 scripts\replay_action_source.py --run public-v13 --report-name 新的英數名稱
.\.venv\Scripts\python.exe -X utf8 scripts\evaluate_public_documents.py --name 新的英數名稱 --isolated
```

真實公文重播需本機的 `.runtime/public-documents/runs/<run>/` 與 `.runtime/action-source-v1/baseline-app.py`；公開檔案不附官方逐字內容。報告拒絕覆寫既有同名檔。基礎模型、提示詞與問答驗證不變，沒有新微調或保留test推論。模型仍可能選錯語意，來源定位不代表完整理解，待辦空欄與公報篇名當地點等其他問題亦未因此解決。

## 實際圖片回歸與採用

public-v14完成5頁、原有20/20欄位片段檢查、10/10問答、0錯誤。兩項額外待辦診斷皆通過；對同批新生成重播，旧版0/2、新版2/2，只改两個action，其餘33欄相同。五頁逐字稿與public-v13一致，九題答案不變，一題只變動空白／標點，日期、郵戳規定及引文內容相同。已在回歸完成後更新本機服務，health SHA256與受測版本一致。

改善有同輸出對照證據，但只針對兩項已知開發失敗，不代表所有待辦都完整。完整限制見 `../public-documents/public-v14-review.json`。
