# 台灣客語本機試聽 v1

使用 FormoSpeech 的 VoxHakka (`formospeech/yourtts-htia-240704`)，固定 revision `e61e1026d1fe5edb29f35ad025c090526a7e4fe7`。模型採 CC BY-NC 4.0，原模型與模型卡由作者提供；本專案沒有重新訓練或改寫權重。模型授權不因程式採 MIT 而改變。

- 來源：https://huggingface.co/formospeech/yourtts-htia-240704
- 上游推論範例：https://huggingface.co/spaces/united-link/taiwanese-hakka-tts
- 漢字轉音標：https://pypi.org/project/formog2p/
- 本機介面目前開放四縣腔與海陸腔，固定使用上游 XF 聲音，不提供聲音複製。

`voxhakka-download.json` 記錄下載檔案雜湊，三個權重檔均比對上游 LFS SHA256。約 1 GB 權重只存於本機 `.runtime/voxhakka`，不打包到 GitHub。

`probe-report.json` 是整合前的隔離實驗；同一句「天公落水」在兩種腔調皆產生有效 22,050 Hz 單聲道音檔，沒有未知音標。CPU 合成階段分別約 1.14 秒與 0.81 秒，**不含 Python 啟動、函式庫匯入及模型載入**。這不是端到端延遲或母語者發音評分。

正式 worker 為 `scripts/hakka_worker.py`，在獨立 Python 3.11 / CPU PyTorch 2.6.0 環境執行，結束後釋放模型記憶體。80 字上限、120 秒逾時；未知字詞或音標會拒絕合成。數字必須先寫成客語讀法。不會將華語公文自動翻譯成客語，使用者仍須提供已核對的客語文字。

驗證重點是完整 token 與有效 waveform、API 的邊界及失敗恢復、瀏覽器操作。尚未完成母語者聽辨、長句韻律或文件翻譯評測，不宣稱語意／發音正確率。

正式 API 及 UI 實測：兩個腔調都由瀏覽器按鈕成功產生播放器；海陸腔音檔長度 2.358 秒，readyState=4、media error=null。見 `ui-validation.json` 與 `workspace.png`。完整測試為 Python 203 項、JavaScript 25 項；JavaScript 數量包含既有測試，客語 UI 另採實際操作驗證。
