# Windows OCR 直接呼叫測試

正式程式改用 PyWinRT 直接呼叫同一個 Windows OCR 引擎，省去每次啟動 PowerShell 的成本。缺少套件、逾時或呼叫失敗時，仍回退到原本 PowerShell 流程。

10 張圖片（2 張原創示範、8 頁公開文件）依正式上傳設定重新編碼為 JPEG quality 93，交替執行兩個 OCR 路徑。10/10 文字完全相同；PowerShell 減去直接呼叫耗時的中位數為 **0.3408 秒**。文字相同不代表辨識正確，也不是一般準確率。計畫與逐張結果見 `plan.json`、`ocr-pairs.json`。

完整圖片 API 另各測一組：補件通知 12.063 → 8.376 秒，社區活動 10.538 → 10.311 秒；兩組全文與七個欄位一致。單次配對受快取、GPU 與其他程序影響，不能把補件通知整段 3.687 秒差距歸因於 OCR，也不能推估平均整體加速。見 `photo-summary.json`。

初次獨立 OCR 探測誤用 quality 92，後來修正重測；本資料夾的 OCR 結果全部取自 quality 93。完整 API 本來就使用 93。未混合兩者計算。

驗證：Python 231 項通過；前端未修改，沿用先前 30 項通過紀錄。新增測試涵蓋字序、英文空格、失敗回退、暫存檔清理與逾時。重測入口：`scripts/benchmark_native_ocr.py`。

依賴：[PyWinRT](https://github.com/pywinrt/pywinrt) 3.2.1（MIT）；Windows OCR 引擎與語言套件由作業系統提供。

實際整合測試發現先呼叫 Windows OCR、再首次載入 torch 會造成 c10.dll / WinError 1114。修復為啟動時先初始化 torch（不載入語音權重），直接 OCR 也有相同保護。修復後全套 231 項測試通過；真實瀏覽器先辨識通知（8.4 秒），再轉寫及播放台語「你好」成功。10 張 OCR 配對也重新執行，以上中位數採最終重測結果。`runtime-init.json` 另記啟動初始化耗時，不含於每張 OCR 計時。前述完整 API 配對為相容性修復前，OCR 演算法及模型設定未變。
