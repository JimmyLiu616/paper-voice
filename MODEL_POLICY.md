# 模型來源政策

生效日期：2026-10-03。依專案擁有者要求，禁止中國機構開發的模型及其衍生權重，包含海外團隊基於中國底模所做的微調、蒸餾、合併與量化。新來源未完成查核前預設拒絕。規則適用於紙聲通正式功能與後續開發／研究，不會限制這台電腦的其他應用程式。

## 現行正式模型

| 功能 | 模型／元件 | 發布者與底模 |
| --- | --- | --- |
| 看圖、中文問答、客語欄位提案 | Google Gemma 3 4B | Google，美國 |
| 台語翻譯 | SARC-Taigi-LLM-12b-GGUF | 臺灣 SARC；Google Gemma 3 12B 底模 |
| 台語朗讀 | MMS TTS nan | Meta，美國 |
| 客語文字 | 本專案來源核對及限定句型 | 無另外的通用客語翻譯權重 |
| 客語朗讀 | VoxHakka / YourTTS | 臺灣 FormoSpeech 團隊；YourTTS 架構 |
| 阿美語翻譯 | ILRDF NLLB 600M | 臺灣原住民族語言研究發展基金會；Meta NLLB 底模 |
| 阿美語朗讀 | MMS TTS ami | Meta，美國 |
| 語音提問 | Taiwan Tongues ASR CE v1.0 | 臺灣團隊／數產署發布；OpenAI Whisper large-v2 底模 |
| 語音活動偵測 | Silero VAD v6 | Silero Team，俄羅斯；隨 faster-whisper 1.2.1 安裝的 ONNX 權重 |
| 系統 OCR／華語朗讀 | Windows OCR／Microsoft Hanhan Desktop | Microsoft，美國；非開源模型 |

查核的是開發機構與公開的權重沿革，不依輸出中文或作者姓名判定來源，也不宣稱已追溯所有上游訓練資料。一般程式庫、字典與模型權重分開辨識：例如 OpenCC 是文字轉換程式，不是中國大模型。第三方模型授權仍各自適用，功能納入正式介面不會改變非商業條款。

一手資料：[Gemma](https://huggingface.co/google/gemma-3-4b-it)、[SARC 底模說明](https://huggingface.co/Speech-AI-Research-Center/SARC-Taigi-LLM-12b)、[VoxHakka 模型](https://huggingface.co/formospeech/yourtts-htia-240704)、[VoxHakka 團隊與方法](https://arxiv.org/html/2409.01548v1)、[ILRDF 模型](https://huggingface.co/ILRDF/nllb-600m-formosan-all-finetune-v2)、[MMS nan](https://huggingface.co/facebook/mms-tts-nan)、[MMS ami](https://huggingface.co/facebook/mms-tts-ami)、[ASR 底模](https://huggingface.co/adi-gov-tw/Taiwan-Tongues-ASR-CE-v1.0)、[Silero VAD](https://github.com/snakers4/silero-vad)、[Silero 官方機構資料](https://silero.ai/about/)。

## 過去曾用過，但現在禁止

- `qwen3:8b`：曾做客語測試，未採用到正式功能。中國阿里巴巴 Qwen。
- `paper-voice-omnitranslate-test:latest`：曾做客語測試，未採用。雖由其他作者發布，[OmniTranslate 1.1 官方模型卡](https://huggingface.co/MihaiPopa-1/OmniTranslate-1.1)明載以 Qwen3-0.6B 微調，因此同樣禁用。
- `qwen3-embedding:0.6b`：本機全域 Ollama 有安裝，未找到紙聲通使用路徑。

以上三個標籤在此次盤點仍已安裝；未刪除使用者可能供其他專案使用的模型。保留歷史失敗紀錄，不把過去曾使用改寫為從未使用。`qavit/mt5-small-hak` 發布者來源與授權尚未通過核准，舊探測腳本現在也會拒絕執行。法國 Mistral 的既有實驗紀錄保留於來源清單，但未加入正式推論清單。

## 執行方式與界線

- `AGENTS.md`、`.cursor/rules/model-origin.mdc` 約束後續開發；`MODEL_POLICY.json` 是核准的固定版本清單。
- `scripts/model_policy.py` 在正式 Ollama 推論與預載前核對標籤及完整 digest，SARC 另核對權重雜湊；別名或新版本不能直接放行。
- 本機 ASR／TTS／NLLB 在載入前核對權重、tokenizer、config 的 SHA256；檔案修改會使快取失效。VAD ONNX 亦列入。
- 正式下載器先檢查模型 ID 與 revision。來源不明、缺檔或版本不符時停止該模型，不自動切到未核准模型或雲端 API。
- 健康檢查的 ready 表示檔案大小／Ollama digest 符合就緒條件；完整檔案雜湊在實際載入前核對。核准清單和程式碼本身是受信任的版本控制檔，不是防止管理員修改的作業系統沙箱。
- 模型升版需先查核來源，再更新 manifest 與測試，不能自動用現有任意權重重建核准雜湊。此次 manifest 的 Hugging Face 檔案已與固定 revision 的官方 Git／LFS 雜湊逐一比對。

本次盤點及功能測試見 [模型來源與三語整合驗證](evaluation/model-origin-v1/README.md)。
