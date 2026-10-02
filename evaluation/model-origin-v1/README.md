# 模型來源政策與正式三語功能驗證

日期：2026-10-03（Asia/Taipei）。此次將台語翻譯、客語生活通知重點解說、阿美語翻譯列為正式整合功能，保留中文對照、自動播放及未驗證品質提示。沒有訓練或替換現行語言模型，也沒有增加人工確認關卡。

## 來源盤點

正式推論使用 Google Gemma、臺灣 SARC／Google、臺灣 FormoSpeech VoxHakka、臺灣 ILRDF／Meta、Meta MMS、臺灣 Taiwan Tongues／OpenAI，以及俄羅斯 Silero 的 VAD。Windows OCR／Hanhan 為 Microsoft 系統元件。依機構與公開底模資料，未發現現行正式流程使用中國來源模型；不等於所有上游訓練資料皆經國別稽核。

本機仍安裝 Qwen3 8B、Qwen3 embedding 0.6B，以及 Qwen 衍生的 OmniTranslate 測試標籤。Qwen 8B、OmniTranslate 曾實際測試但未部署，不能宣稱本專案歷史上從未使用中國模型；embedding 未找到專案呼叫。此次未刪除全域模型。舊報告加註禁用，未知來源的 mT5 探測入口也停止啟用。

`inventory.json` 保存首次盤點；`audit.json` 是後續唯讀檢查，正式八項模型（含 VAD）均通過指定版本或檔案 SHA256 核對。Hugging Face 的本機權重與附屬檔案另與官方固定 revision 的 Git／LFS 雜湊比對後才建立 `MODEL_POLICY.json`。

## 規則與回歸

- 常駐規則：`AGENTS.md`、`.cursor/rules/model-origin.mdc`；政策與一手來源：根目錄 `MODEL_POLICY.md`。
- 正式 Ollama 載入前核對標籤與 digest；本機翻譯／TTS／ASR／VAD 核對固定檔案。新下載須使用核准 ID／revision。
- `tests/test_model_policy.py` 涵蓋 Qwen／DeepSeek／衍生／未知模型拒絕、更名但 digest 不符、相同大小權重置換、缺檔、可讀 API 錯誤及客語不吞掉政策錯誤。
- 台語就緒條件包含 SARC 翻譯與 MMS 語音，避免僅安裝 TTS 就誤顯示整條翻譯管線就緒。
- 352 項 Python、49 項 JavaScript 通過；原有 Starlette TestClient deprecation warning 保留，未為此更動依賴。

## 實際介面測試

使用自製「本活動免費，不必繳費。」通知及「需要繳費嗎？」問題。`browser-check.json` 保存三語的中文、譯文、播放完成狀態及音長；音長／播放成功不等於母語品質評分。此次未評估阿美語非秀姑巒語別，或客語其他聲音。

也保留一筆客語拒絕案例：帶「社區活動通知（自製測試）」標題的內容被來源恢復一起交給客語時，標題不在支援句型中，整段停止且沒有語音。沒有靜默略過標題來宣稱全段完成。移除標題的支援完整句另行測試；這是功能範圍限制，仍待改善來源段落定位的通用性。

## 重現

```powershell
.venv/Scripts/python.exe -X utf8 scripts/audit_models.py --check-files
.venv/Scripts/python.exe -X utf8 -m pytest -q
node --test tests/*.test.cjs
```

開啟本機頁面，在「多語翻譯與朗讀」選語言，再提問或重讀既有回答。此政策約束本專案，並非對整台電腦的系統封鎖；不會停止其他應用程式或替使用者刪除模型。

另外以既有自製合成華語音檔實測 ASR／VAD 新檢查路徑，成功輸出「我需要準備什麼文件」。結果見 asr-check.json；這不是真人語音品質評測。
