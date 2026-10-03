## 動態文件重點與語音匯出

上傳照片或貼上文字後，依文件原有段落、章節產生不同主題的重點，不再顯示固定七欄。每點提供白話文字、辨識原文行號與引文，也可單獨朗讀。小模型逐段處理，再做 AI 比對及數字／單位／關鍵限制檢查；未通過時保留原文。這些檢查不是正確性證明，OCR 錯字仍會影響摘要。

- 下載重點 TXT：重點、原文依據、朗讀稿與全文。
- 下載依據 JSON：`paper-voice-summary-v2` 結構，含 `highlights`、`source_lines`、`narration_text`、提醒；`fields` 僅為歷史相容而保留空陣列。
- 用所選語言朗讀：完整完成後播放，可下載 WAV 與中譯對照 TXT，逐段標示播放位置。沒有產生完整音檔時不提供部分文件錄音。
- 中文可朗讀長文件；台語／阿美語每句仍限 80 字，客語仍限已支援句型。超出範圍請選單項重點，或改用中文，不會偷偷截斷或省略內容。

`/api/analyze` 與 `/api/analyze-text` 已改用動態摘要；`/api/narrate-document` 只根據目前工作結果產生語音，避免畫面與音檔來源不同。舊固定欄位驗證器保留供歷史評測，不是目前畫面或正式摘要路徑。舊版欄位評分不可作為新版摘要成效。

# 紙聲通 Paper Voice

原始碼：[JimmyLiu616/paper-voice](https://github.com/JimmyLiu616/paper-voice)。這是需要在 Windows 安裝並執行的本機應用，GitHub 頁面提供程式與說明。

[示範影片與實驗權重下載](https://github.com/JimmyLiu616/paper-voice/releases/tag/v0.1.0-demo) · [LoRA 實驗權重、授權與載入說明](training/ADAPTER_RELEASE.md)。正式應用仍使用原版 Gemma 3；下載實驗 adapter 不是執行應用的必要步驟。

在 Windows 本機運行的生活文書識讀原型：圖片 → 本機 OCR 輔助 → Google Gemma 3 VLM 核對 → 重要欄位 → 中文朗讀及文件問答。加入數產署 Taiwan Tongues ASR CE 語音提問；使用統一語言選單提供華語、台語、客語、阿美語的回答翻譯朗讀，並保留自願修正語料匯出。

目前主攻生活通知／公文的期限、應備文件、費用與例外條件。逐輪開發評測與失敗案例見 `ITERATION_LOG.md`，可執行的合成基準見 `evaluation/README.md`。獨立 Ministral 3 3B 合成單批 QLoRA 已通過權重更新及跨程序重載檢查，見 `training/LORA_SMOKE.md`；僅證明短文字配置能在本機訓練，尚無公文任務改善證據，未部署 adapter。

已另提供經核對資料的[文件 LoRA 訓練入口](training/DOCUMENT_LORA.md)，包含原模型／adapter 開發題輸出比較與執行紀錄。共用 CUDA 流程已以固定合成素材完成一次權重更新、保存與獨立程序重載；生成答案未改變，沒有任務改善證據。2026-10-02已完成首次具核對聲明的32任務微調，格式改善但新增否定題拒答，未採用。資料分組、完整輸出及限制見[首次任務微調](training/REVIEWED_RUN_001.md)。第二輪僅將學習率減半，恢復禁止題回答但新增例外欄漏列，仍未採用，見[第二次任務微調](training/REVIEWED_RUN_002.md)。

下一批是[6份禁止／例外成對訓練草稿](training/CONTRAST_REVIEW.md)，針對明確規定與文件未提供、完整文件清單及費率條件。啟動後可在[新增核對頁](http://127.0.0.1:8765/static/training-review-contrast.html)逐份核對；目前皆未確認，不會直接用於訓練。原本12份的確認紀錄分開保存。

新版約 77 秒的[多語示範影片](https://github.com/JimmyLiu616/paper-voice/releases/tag/v0.2.0-languages-demo)包含台語轉寫與四縣客語試聽；為實際操作畫面取樣及另配旁白，非原生連續錄影。

## 正式多語功能與模型來源

台語翻譯朗讀、客語生活通知重點解說、阿美語翻譯朗讀已納入正式功能，透過同一選單切換並自動播放，保留中文對照。操作與支援範圍見 [LANGUAGES.md](LANGUAGES.md)。正式入口不代表翻譯品質已通過母語者驗證，客語仍為限定場景解說。

依使用者要求，專案禁止中國機構模型及其衍生權重。現行正式流程未使用中國來源模型；歷史上曾測 Qwen 與 Qwen 衍生 OmniTranslate，現在均禁用。本機仍安裝不代表本專案會呼叫。規則、底模沿革、核准清單及檔案檢查見 [MODEL_POLICY.md](MODEL_POLICY.md)。

## 開始使用

首次使用請先完成下方「在另一台 Windows 重建」；已完成環境及模型安裝後，可依以下步驟操作。

1. 雙擊 `Start.cmd`。
2. 開啟 <http://127.0.0.1:8765>。
3. 點「補件通知」或「社區活動」，再點「幫我讀懂」。這會真正呼叫本機模型，不是預先寫好的辨識結果。
4. 在「多語翻譯與朗讀」選華語、台語、客語或阿美語；客語可選四縣／海陸，阿美語可選譯文語別。
5. 輸入中文問題，按「提問並朗讀」。畫面先顯示中文回答及原文依據，再自動翻譯並播放所選語言，不需勾選人工確認。
6. 切換語言後按「用此語言重讀」，沿用相同回答；每筆舊回答也有「用所選語言聽這個回答」。按「停止」、換語言或換文件會丟棄遲到的音檔。
7. 也能錄音提問／選音檔，核對轉寫文字後按「提問並朗讀」；或用文件卡的「用所選語言朗讀」聽重要資訊／整份辨識原文。
8. 修正原文後，按「預覽這次辨識修正」，去識別化及授權確認後下載 JSONL；不會自動上傳。

華語單次最多 1,800 字；台語／阿美語最多 6 個完整短句、每句 80 字；客語來源最多 6 段、每段 160 字，逗號與分號不拆開，超限不截斷。只有整份選定內容成功合成才播放，失敗時保留中文及已產生的譯文並說明原因。客語以支援範圍內的公文重點句型解說；翻譯草稿自動播放不代表語意、數字或發音已驗證。

直接拍攝：在「上傳圖片」按「開啟攝影機拍文件」→「啟動預覽」，允許瀏覽器使用攝影機；對焦後按「拍照」，可重拍或「使用照片並辨識」。照片確認前只在瀏覽器記憶體，確認後交給同一個本機圖片辨識 API。拍照、關閉視窗、切換到其他頁面時會停止相機。支援切換瀏覽器提供的攝影機，不擷取麥克風聲音。

攝影機需瀏覽器支援並取得相機權限。若內建瀏覽器無法使用，可在電腦的 Edge／Chrome 開啟同一個 `http://127.0.0.1:8765` 網址。此版仍僅綁定本機；手機無法透過自己的 `127.0.0.1` 連到電腦，手機遠端拍攝需要另行配置安全連線。

停止服務：雙擊 `Stop.cmd`，只會停止由本專案啟動器啟動且 PID／啟動時間／程式路徑相符的服務。它不會停止 Ollama 或其他專案。

服務僅綁定 `127.0.0.1`，目前只供本機瀏覽器使用，手機無法直接連入。不會自動修改防火牆或公開服務。

## 已實作

- 縮短本機結果查詢間隔；6 次同一工作配對量測，完成後收到結果的等待時間中位數由 0.77 秒降至 0.15 秒。這不代表模型本身加速，見 [結果回傳實測](evaluation/result-delivery-v1/README.md)。
- JPG／PNG／WebP 單頁辨識，最大 12 MB、2,400 萬像素；EXIF 方向校正、縮圖及移除 EXIF。
- 瀏覽器攝影機预覽、拍照、重拍、確認後辨識；JPEG 最長邊 2,400 像素，拍下後立即停止相機。
- Google Gemma 3 4B 量化 VLM 真實讀圖，Windows OCR 提供額外文字線索；無 Windows OCR 時仍可用 VLM。PyWinRT 直接呼叫在 10 張配對圖片中與原流程文字一致，OCR 階段中位數少 0.34 秒；不代表整體推論同比例加速，見 [實測](evaluation/native-ocr-v1/README.md)。
- 行動、辦理期限、地點、應備文件、聯絡資訊、費用及適用條件／例外。
- 有明示標題的公文跨行段落／編號清單保留來源，期限帶回郵戳或適用條件；隨函附件不直接當成應備文件。多欄、掃描錯字仍可能影響語意，詳見公開公文測試報告。
- 獨立「應備文件」標題後可保留編號清單；遇到獨立的「※說明／備註」會結束前段，避免費用卡混入下一節標題。仍須核對 OCR 字詞及不同身分的適用條件。
- 值與引文皆需對應辨識原文，否則顯示待確認。這項檢查不能證明原圖讀對，也不能證明回答語意完全正確。
- 例外文字正確但引用錯配時，僅在唯一完整原文行可逐字定位且沒有省略前後條件時恢復；原有其他例外仍保留於提醒。已修復1項公文開發案例，不能保證所有條件完整，見 `evaluation/condition-source-v1/`。
- 文件清單被模型改成頓號／換行格式時，只有每項皆依序對應有效引文、且原文明確要求準備，才恢復完整原文段落；不把原文概稱的其他文件補成完整清單。見 `evaluation/document-list-source-v1/`。
- 待辦優先保留唯一明示辦理方式的完整段落，包含線上／紙本選項；不把「申請補助」中的「請補」當指令。明確跨行代辦條件可接回，原始OCR錯字不改寫，見 `evaluation/action-source-v1/`。
- 保留 Gemma 與 Windows OCR 文字；可手動修正並重新整理。
- Taiwan Tongues ASR CE v1.0 本機語音辨識，文字確認後送入文件問答，答案可用中文朗讀。
- 基於目前文件的文字問答與原文引文。無有效引文時回覆無法從文件確認。
- 回答語音預設包含原文引用，以明確口語提示分開兩者，方便核對短答可能省略的日期或條件。這不會修正模型答案，也不能保證引用支持答案或 OCR 正確。
- Windows 台灣華語離線 WAV、播放／停止／重播／速度調整。
- 台語、客語、阿美語本機翻譯／解說及自動朗讀，詳見 [正式多語功能](LANGUAGES.md)。
- 自願文字修正語料預覽、規則初篩個資、人工確認、JSONL 本機匯出。詳見 `CONTRIBUTING_DATA.md`。
- 大字模式、窄螢幕排版、JSON 匯出、兩份原創虛構示範文件。

## 目前沒有宣稱完成

- 免人工核對的可靠台語翻譯、台語口音品質驗證、真人麥克風／台語／客語辨識品質驗證。
- 競賽加分認定、已對外發布語料集。指定 ASR 已實質介接，是否獲加分仍由評審決定。
- 已證明能改善理解品質的微調模型、手寫帳單可靠辨識、PDF 多頁、跨文件 RAG、逐字影像框選。
- 醫療用法判斷、法律效力判斷、未明示日期的自動推算。
- 目標族群使用者研究、整體準確率或效益提升數據。

## 本機設備與資源

本專案測試設備為 NVIDIA RTX 5060 Laptop GPU 8GB、約 16GB 系統記憶體。

- Gemma：Ollama `gemma3:4b`，約 3.3GB 下載，量化格式 Q4_K_M。模型位於既有 Ollama 模型儲存區。
- TTS：Meta MMS 約 36.3M 參數，放在 `.runtime/mms-tts-nan`，CPU 推論，避免與 VLM 爭用 GPU。
- ASR：指定 v1.0 權重約 3.1GB，`.runtime/taiwan-tongues-asr`；CPU int8、4 執行緒，每次完成後卸載程序，避免占用顯卡。短句約十多秒，並非即時串流。
- 中文語音：已確認 `Microsoft Hanhan Desktop`／`zh-TW` 可用。此為 Windows 聲音，不是開源 TTS 權重。
- 後端：FastAPI + Python；前端：原生 HTML/CSS/JavaScript，無外部 CDN。

其他 GPU 工作占滿顯存時，Ollama 可能變慢。先結束不需要的模型工作；不要任意停止他人的服務。

## 在另一台 Windows 重建

需要 Python 3.11 以上、Ollama、Windows 繁中語音／OCR 語言元件。先從 GitHub 的 Code → Download ZIP 下載並解壓，或使用下列 Git 指令；接著在專案目錄執行安裝。

```powershell
git clone https://github.com/JimmyLiu616/paper-voice.git
cd paper-voice
```

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull gemma3:4b
.\.venv\Scripts\python.exe scripts\download_taigi.py
.\.venv\Scripts\python.exe scripts\download_asr.py
.\.venv\Scripts\python.exe scripts\make_samples.py
.\Start.cmd
```

若要使用 CPU 版 PyTorch，可改從 PyTorch 官方 CPU index 安裝；本機實際套件版本記錄於 `requirements-lock.txt`。重建時請以對應平台套件及 `requirements.txt` 為準，`+cpu` 版本需對應的官方 index。

首次下載模型需要網路。下載完成後，核心辨識、Windows 華語及 MMS 閩南語推論均在本機執行，不需付費雲端 API。統一介面使用固定本機模型與 Microsoft Hanhan Desktop，沒有啟用來源未核准的瀏覽器語音備援。

MMS 與指定 ASR 的下載程式固定使用 `MODEL_SOURCES.json` 所記錄的 revision。Ollama 的 `gemma3:4b` 標籤可能更新；重建後請比對該檔的 digest，新版本應重新查核來源並更新 MODEL_POLICY.json、重新測試；版本不符會拒絕載入，不能直接沿用既有評測結果。

## API 與程式結構

```text
app.py                    本機 API、模型呼叫、引文驗證、工作佇列、TTS
static/                   前端頁面與樣式
scripts/speech.ps1        Windows 台灣華語聲音與 WAV
scripts/ocr.ps1           Windows OCR 文字及位置
scripts/download_taigi.py 固定 revision 下載 Meta MMS
scripts/make_samples.py   建立原創測試文件
scripts/smoke_test.py     實際模型端到端驗證
tests/test_app.py         資料邊界及引文處理測試
samples/                 原創虛構文件，沒有真實個資
.runtime/                忽略於版本控制的模型、快取與執行紀錄
```

API 文件：<http://127.0.0.1:8765/api/docs>。POST／DELETE 需帶 `X-PaperVoice: local-ui`，前端已處理。Swagger 內執行請另提供此標頭；此標頭是本機跨來源請求防護，不是使用者身分驗證。

```text
GET    /api/health          Ollama、模型與台語權重狀態
GET    /api/voices          實際 Windows 聲音清單
POST   /api/analyze         上傳圖片，回傳工作 ID
POST   /api/analyze-text    整理人工確認文字
GET    /api/jobs/{id}       查看階段、結果或錯誤
DELETE /api/jobs/{id}       清除記憶體內工作
POST   /api/ask             文件問答
POST   /api/speech          產生 Windows 華語／MMS 閩南語 WAV
POST   /api/transcribe      音檔 -> 指定 ASR -> 待人工確認的問題
POST   /api/narrate         中文回答／內容 + language + dialect -> 翻譯草稿 + WAV base64
POST   /api/document-taigi  舊版相容 API，非新版介面流程
POST   /api/corpus/preview  修正文字對與初步個資遮蔽
POST   /api/corpus/export   人工確認後下載語料，不上傳
```

## 資料處理

準備微調資料可使用 [訓練資料核對頁](http://127.0.0.1:8765/static/training-review.html)：提供 12 份原創虛構通知、36 題問答草稿，供你或老師逐份核對與匯出。未確認的草稿不能當人工標註；公開草稿預設未確認，不會自動訓練。本機已另保存12份確認聲明並於首次實驗固定8/2/2分組；保留test尚未推論。操作及暫存／下載限制見 [核對流程](training/REVIEW_WORKFLOW.md)。

文件不送第三方雲端 AI API，不寫入資料庫。ASR 音檔及轉寫結果只在系統暫存目錄短暫保存，完成或逾時後刪除。Windows OCR 必須使用短暫圖片檔，Windows TTS 必須使用短暫文字／WAV；放於作業系統暫存目錄（預設 `%TEMP%`）的 `paper-voice-ocr-*` 或 `paper-voice-speech-*` 隨機資料夾，處理完成後刪除。上傳文件不寫入專案目錄，避免專案位於雲端同步資料夾時被一併同步。程式遭強制終止時可能留下暫存檔，請依上述前綴檢查系統暫存目錄。

結果在程序記憶體最多保存 30 分鐘，最多保留 20 個工作，可手動清除。關頁時嘗試刪除，但瀏覽器不保證送達。匯出 JSON 是使用者主動保存，可能含原文，請自行管理。測試紀錄只含自製範例。

## 測試

```powershell
.\.venv\Scripts\python.exe -m pytest -q
# 先啟動本機服務，再執行真正呼叫模型的驗證：
.\.venv\Scripts\python.exe -X utf8 scripts\smoke_test.py
.\.venv\Scripts\python.exe -X utf8 scripts\validate_asr.py
.\.venv\Scripts\python.exe -X utf8 scripts\validate_extensions.py
# 若有 Node.js，可驗證相機生命週期（使用合成串流，不會開啟實體相機）
node --test tests\camera.test.cjs
```

測試結果限於自製範例，不能當成未見文件或目標族群的準確率。MMS 產生有效 WAV 不等於已驗證台灣台語發音品質。模型政策可另執行 `.venv/Scripts/python.exe -X utf8 scripts/audit_models.py --check-files` 唯讀檢查；它會分列專案核准權重與本機其他已安裝標籤。

## 授權與參賽

原創程式碼與虛構文件圖片採 MIT；修正語料格式示例與自願匯出資料採 CC BY 4.0，詳見 `CONTRIBUTING_DATA.md`。Gemma、Meta MMS、Taiwan Tongues ASR CE（TRAIL）、Windows 語音及套件各自保留原授權，不能用本專案 MIT 重新授權它們。

完整模型來源見 `MODEL_SOURCES.json`；企畫及展示流程見 `SUBMISSION.md`。原始碼公開於 [GitHub](https://github.com/JimmyLiu616/paper-voice)，模型權重與使用者文件不隨儲存庫發布。公開原始碼不等於已提交競賽報名，也不代表主辦已確認參賽資格或加分。

第二次[learning-rate受控比較](training/REVIEWED_RUN_002.md)恢復了否定題回答，但例外欄新增漏列、格式改善消失，仍未採用；兩輪原模型基準相同，保留test未推論。

2026-10-02 ASR前置檢查：使用原VAD設定提前拒絕無語音輸入，真實模型配對測試的點擊聲／純音／白雜音由8–12秒降至約0.58秒，且不載入ASR模型；靜音原已早退。四筆合成華語轉寫內容相同，一般語音延遲未一致改善。完整Python183項通過，正式API的兩筆拒絕及一筆合成語音轉寫亦通過。每例一次、無真人或台語品質結論，沒有權重更新。見 [ASR實測](evaluation/asr-preflight-v1/README.md)。

2026-10-02照片等待改善：開啟工作台時提前載入本機模型，選照片時可看到準備狀態。兩張自製圖片預載完成後，上傳到結果由28.9／25.5秒變為8.3／7.5秒，全文及七欄一致；預先載入本身仍需20.5／19.1秒，不能說總計算時間或每次推論快了三倍。189項Python、25項JavaScript通過。縮短欄位輸出及直接使用OCR的候選因漏資訊未採用，紀錄見 [照片速度實測](evaluation/photo-latency-v1/README.md)。影片仍為較早版本。


## 客語語音安裝（正式功能、本機）

在「多語翻譯與朗讀」選客語，再提問或重讀回答，系統會產生限定句型的客語草稿並自動以四縣腔或海陸腔朗讀。模型為 [FormoSpeech VoxHakka](https://huggingface.co/formospeech/yourtts-htia-240704)，CC BY-NC 4.0，固定 XF 聲音。每個完整語音片段最多 80 字；支援的日期、金額及歲數會轉成漢字數詞草稿，不支援的句型會整段拒絕，不會只翻譯前半句。這是本機規則轉換，並非通用翻譯模型；客語自然度及數字讀法仍須人工核對。

既有華語使用 Windows 台灣華語；台語由 SARC 產生翻譯草稿，再以 Taibun 轉白話字、Meta MMS 合成。不能宣稱公文已能無人核對地轉成正確台語或客語。

先依上述步驟建立主程式 `.venv`，並安裝 Python 3.11 與 uv，再執行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_hakka.ps1
```

此步驟建立獨立 `.venv-local-tts`，下載約 1 GB 上游權重及 CPU 語音套件。初始化需要網路，之後語音合成離線；不占用文件辨識的 GPU。版本清單在 `scripts/hakka-requirements-lock.txt`，模型 revision、授權與 SHA256 在 `MODEL_SOURCES.json` 和 `evaluation/hakka-v1/`。權重與虛擬環境不會上傳 GitHub。


## 台語讀音轉換

台語轉寫現為統一朗讀流程的內部步驟：SARC 譯文 → 漢字數詞讀音 → Taibun 白話字 → MMS。未知字或不支援的數字不會直接略過；不能完整轉寫時保留中文與譯文，回報語音未完成。

更新套件：`.venv/Scripts/python.exe -m pip install -r requirements.txt`。新增依賴為 Taibun 1.1.8 / msgpack 1.1.2，台語聲音使用原有 MMS 模型，單純漢字轉寫無需下載另一個大型模型；自動翻譯草稿另需下方的 SARC GGUF。首次台語模型載入較久；後續短句測試約 0.3–0.6 秒，不代表其他文件或設備的速度。

Taibun 程式 MIT，字詞資料依套件聲明為 CC BY-SA 4.0；Meta 聲音模型 CC BY-NC 4.0。鼻音上標的模型輸入轉換、實測限制與來源見 `evaluation/taigi-hanji-v1/README.md`。台語及客語發音均尚待母語者驗證。


## 台語翻譯朗讀（正式功能、本機）

此電腦已安裝約 6.48 GB 的 SARC 12B Q3_K_L。其他電腦可先執行：

```powershell
ollama pull hf.co/Speech-AI-Research-Center/SARC-Taigi-LLM-12b-GGUF:Q3_K_L
```

程式只接受模型權重 SHA256 `cd88bdf097e74696de3b4bf1eb9fa55e8dc3bb309521b2a458ff0a4660583d71`；若上游標籤更新，會拒絕版本不符，請依評測計畫指定 revision 取得原檔，不略過檢查。模型來源與授權見 `MODEL_SOURCES.json`。

在統一選單選台語 → 提問並朗讀，或重讀既有回答。阿拉伯數字先以標記保護，驗證數量、順序及常見單位後才還原。日期／金額／數量中的 0–9999 整數可轉為漢字數詞讀音草稿；前導零、電話、編號、小數與其他不支援格式仍要求人工處理。保留原數字的譯文與數詞草稿分開顯示，檢查不等於語意正確。

8 GB 顯卡會在 Gemma 文件模型與 SARC 翻譯模型間切換，首次約需數十秒。翻譯請求結束後釋放 SARC，再於背景準備 Gemma，期間新翻譯可能提示忙碌。這不是照片加速項目。舊版 `/api/taigi-translation` 仍限文件原文；新版 `/api/narrate` 接受中文回答／內容，直接串接翻譯與合成，無人工確認步驟。

試驗結果及已知限制見 [翻譯草稿驗證](evaluation/taigi-translation-v2/README.md)。台語的自然度與口音仍待母語者評估；客語另有生活通知限定句型轉換，並非通用翻譯。既有 77 秒示範影片錄於此功能加入前，未展示翻譯草稿。

讀音草稿對「逾期不受理／仍須繳費」提供有辭典依據的口語詞替換，保留原譯文並在畫面揭露替換；其他缺詞仍要求人工核對，詳見翻譯草稿驗證。


## 客語公文重點解說（全本機）

在「多語翻譯與朗讀」選客語與四縣／海陸腔，提問後自動解說朗讀，也可切換語言再按「用此語言重讀」。不需進入實驗室或每次人工確認。

新流程為「中文文件／問題 → 本機問答 → 完整原文段落 → 結構化欄位 → 來源核對 → 客語句型 → VoxHakka」。支援期限與時刻、應備文件、年齡／費用、已登記或繳費的例外、委託書、紙本限制、假日順延與不退費等限定範圍。例如「只有65歲以上才免費，其他人須繳500元」會保留年齡比較及其他人的費用，不交給翻譯模型自由改寫。

Gemma 提案必須與完整來源規則相符；不符時僅使用原文已完整通過規則的結果，明確記錄退回來源規則。未知條件、模糊分組或任一不支援段落會停止整份客語語音並保留中文。問答引文過短時恢復完整原文段落及相鄰明確連接的例外；重複來源無法唯一定位時不任選。畫面可查看本次解說依據。

客語每次最多六段完整來源，每段一百六十字；組句及數字讀法轉換後，每個完整語音片段仍最多八十字。這不是任意中文的通用翻譯，也不能保證恢復文件其他位置的所有相關例外。句型與發音尚未經母語者驗證；兩腔共用文字草稿，由語音模型切換腔調。

貼上 `samples/hakka-notice.txt` 可展示費用、期限與文件問答。程式、11 個本機案例、兩腔實際語音與限制見 [客語重點解說驗證](evaluation/hakka-notice-v2/README.md)。公開候選 `qavit/mt5-small-hak` 的 80 次提示／解碼探測有日期與門檻失真，未接入正式流程，見 [mT5 實測](evaluation/hakka-mt5-v1/README.md)。

舊版整句轉換 API 保留相容，歷史記錄見 [客語中文轉換驗證](evaluation/hakka-translation-v1/README.md)。任意中文也可另評估[客委會官方翻譯服務](https://speech.hakka.gov.tw/Translation/Online)及申請 API，目前沒有串接雲端服務。


## 阿美語翻譯朗讀（正式功能、本機）

在「多語翻譯與朗讀」選阿美語與譯文語別，輸入中文問題並按「提問並朗讀」，或重讀既有回答。系統直接將 NLLB 譯文交給 MMS 合成並自動播放，不要求人工核對或確認勾選。瀏覽器若阻擋自動播放，可按音檔播放器。

新增電腦需先在專案根目錄執行：

```powershell
.venv/Scripts/python.exe scripts/download_amis.py
```

下載固定 revision 的 ILRDF NLLB 600M 與 Meta MMS Amis，約 2.65 GB；下載器驗證權重 SHA256。推論離線使用 CPU，每次請求釋放翻譯模型後再載入語音模型，避免占用既有文件模型的 GPU。API：`POST /api/amis-translate-speak`，欄位 `source`、`dialect`（預設 `ami_Xiug`）、可選 `job_id`；回傳中文、譯文及 WAV base64，沒有 `confirmed` 欄位。超時 180 秒。停止或修改輸入會取消前端等待，已開始的本機合成可能繼續至結束，但舊結果不會播放。

秀姑巒、海岸、恆春、馬蘭、南勢是**譯文語別**，五者共用同一 MMS 阿美語聲音，未驗證各語別發音匹配。AI 草稿可能誤譯或漏譯，日期、金額、否定與例外不能視為已正確翻譯；原文與譯文並列。保留喉塞音：NLLB 的 U+02BC 撇號映射至 MMS 的 ASCII 撇號；其餘不支援字元不會靜默刪掉，合成失敗仍顯示譯文。

兩模型皆 CC BY-NC 4.0（非商業），來源、固定版本及下載驗證見 `MODEL_SOURCES.json`、`evaluation/amis-v1/`。原始碼授權不會覆蓋模型授權；GitHub 不包含權重。主畫面已統一各語言的回答翻譯朗讀流程，舊版各語言 API 保留相容。既有示範影片尚未包含阿美語功能。

最新整合介面實測見 [統一語言問答朗讀](evaluation/unified-narration-v1/README.md)。舊版實驗室截图及影片為歷史紀錄。
