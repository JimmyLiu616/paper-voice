# 紙聲通 Paper Voice

原始碼：[JimmyLiu616/paper-voice](https://github.com/JimmyLiu616/paper-voice)。這是需要在 Windows 安裝並執行的本機應用，GitHub 頁面提供程式與說明。

[示範影片與實驗權重下載](https://github.com/JimmyLiu616/paper-voice/releases/tag/v0.1.0-demo) · [LoRA 實驗權重、授權與載入說明](training/ADAPTER_RELEASE.md)。正式應用仍使用原版 Gemma 3；下載實驗 adapter 不是執行應用的必要步驟。

在 Windows 本機運行的生活文書識讀原型：圖片 → 本機 OCR 輔助 → Google Gemma 3 VLM 核對 → 重要欄位 → 中文朗讀及文件問答。加入數產署 Taiwan Tongues ASR CE 語音提問；另提供人工翻譯後的 Meta MMS 閩南語白話字朗讀與自願修正語料匯出。

目前主攻生活通知／公文的期限、應備文件、費用與例外條件。逐輪開發評測與失敗案例見 `ITERATION_LOG.md`，可執行的合成基準見 `evaluation/README.md`。獨立 Ministral 3 3B 合成單批 QLoRA 已通過權重更新及跨程序重載檢查，見 `training/LORA_SMOKE.md`；僅證明短文字配置能在本機訓練，尚無公文任務改善證據，未部署 adapter。

已另提供經核對資料的[文件 LoRA 訓練入口](training/DOCUMENT_LORA.md)，包含原模型／adapter 開發題輸出比較與執行紀錄。共用 CUDA 流程已以固定合成素材完成一次權重更新、保存與獨立程序重載；生成答案未改變，沒有任務改善證據。2026-10-02已完成首次具核對聲明的32任務微調，格式改善但新增否定題拒答，未採用。資料分組、完整輸出及限制見[首次任務微調](training/REVIEWED_RUN_001.md)。第二輪僅將學習率減半，恢復禁止題回答但新增例外欄漏列，仍未採用，見[第二次任務微調](training/REVIEWED_RUN_002.md)。

下一批是[6份禁止／例外成對訓練草稿](training/CONTRAST_REVIEW.md)，針對明確規定與文件未提供、完整文件清單及費率條件。啟動後可在[新增核對頁](http://127.0.0.1:8765/static/training-review-contrast.html)逐份核對；目前皆未確認，不會直接用於訓練。原本12份的確認紀錄分開保存。

新版約 77 秒的[多語示範影片](https://github.com/JimmyLiu616/paper-voice/releases/tag/v0.2.0-languages-demo)包含台語轉寫與四縣客語試聽；為實際操作畫面取樣及另配旁白，非原生連續錄影。

## 開始使用

首次使用請先完成下方「在另一台 Windows 重建」；已完成環境及模型安裝後，可依以下步驟操作。

1. 雙擊 `Start.cmd`。
2. 開啟 <http://127.0.0.1:8765>。
3. 點「補件通知」或「社區活動」，再點「幫我讀懂」。這會真正呼叫本機模型，不是預先寫好的辨識結果。
4. 查看每個欄位的原文依據，核對圖片，按「聽重點」。
5. 試問「需要準備什麼？」及文件沒有提供的問題，例如「可以搭哪一路公車？」。
6. 用「錄音提問」或選擇音檔（最長 30 秒、8 MB），等 ASR 填入文字後核對，再按「提問」。有引用的答案預設可點「聽回答與依據」，先聽回答，再聽完整引用；取消「同時朗讀原文依據」可只聽回答。拒答或無引用時只讀回答。單次超過 1,800 字會提示縮小問題範圍，不截斷內容。
7. 「台語聲音實驗室」可帶入文件片段，由台語使用者翻譯成台語漢字、轉寫白話字並確認後播放；也可直接輸入白話字或單獨試聽。不自動翻譯。
8. 修正原文後，按「預覽這次辨識修正」，人工去識別化及授權確認後下載 JSONL；不會自動上傳。

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
- Meta `facebook/mms-tts-nan` 離線閩南語白話字 TTS（實驗）。
- 自願文字修正語料預覽、規則初篩個資、人工確認、JSONL 本機匯出。詳見 `CONTRIBUTING_DATA.md`。
- 大字模式、窄螢幕排版、JSON 匯出、兩份原創虛構示範文件。

## 目前沒有宣稱完成

- 中文自動翻譯成台語、台語口音品質驗證、真人麥克風／台語／客語辨識品質驗證。
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

首次下載模型需要網路。下載完成後，核心辨識、Windows 華語及 MMS 閩南語推論均在本機執行，不需付費雲端 API。選擇「瀏覽器語音」時，是否離線取決於瀏覽器提供的聲音，不能等同 Windows 離線模式。

MMS 與指定 ASR 的下載程式固定使用 `MODEL_SOURCES.json` 所記錄的 revision。Ollama 的 `gemma3:4b` 標籤可能更新；重建後請比對該檔的 digest，新版本應重新測試，不能直接沿用本機既有評測結果。

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
POST   /api/document-taigi  文件原文片段 + 人工確認 POJ -> WAV
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

測試結果限於自製範例，不能當成未見文件或目標族群的準確率。MMS 產生有效 WAV 不等於已驗證台灣台語發音品質。

## 授權與參賽

原創程式碼與虛構文件圖片採 MIT；修正語料格式示例與自願匯出資料採 CC BY 4.0，詳見 `CONTRIBUTING_DATA.md`。Gemma、Meta MMS、Taiwan Tongues ASR CE（TRAIL）、Windows 語音及套件各自保留原授權，不能用本專案 MIT 重新授權它們。

完整模型來源見 `MODEL_SOURCES.json`；企畫及展示流程見 `SUBMISSION.md`。原始碼公開於 [GitHub](https://github.com/JimmyLiu616/paper-voice)，模型權重與使用者文件不隨儲存庫發布。公開原始碼不等於已提交競賽報名，也不代表主辦已確認參賽資格或加分。

第二次[learning-rate受控比較](training/REVIEWED_RUN_002.md)恢復了否定題回答，但例外欄新增漏列、格式改善消失，仍未採用；兩輪原模型基準相同，保留test未推論。

2026-10-02 ASR前置檢查：使用原VAD設定提前拒絕無語音輸入，真實模型配對測試的點擊聲／純音／白雜音由8–12秒降至約0.58秒，且不載入ASR模型；靜音原已早退。四筆合成華語轉寫內容相同，一般語音延遲未一致改善。完整Python183項通過，正式API的兩筆拒絕及一筆合成語音轉寫亦通過。每例一次、無真人或台語品質結論，沒有權重更新。見 [ASR實測](evaluation/asr-preflight-v1/README.md)。

2026-10-02照片等待改善：開啟工作台時提前載入本機模型，選照片時可看到準備狀態。兩張自製圖片預載完成後，上傳到結果由28.9／25.5秒變為8.3／7.5秒，全文及七欄一致；預先載入本身仍需20.5／19.1秒，不能說總計算時間或每次推論快了三倍。189項Python、25項JavaScript通過。縮短欄位輸出及直接使用OCR的候選因漏資訊未採用，紀錄見 [照片速度實測](evaluation/photo-latency-v1/README.md)。影片仍為較早版本。


## 客語朗讀（選用、本機）

目前可在「客語實驗室」輸入已核對的客語漢字，切換四縣腔與海陸腔。模型為 [FormoSpeech VoxHakka](https://huggingface.co/formospeech/yourtts-htia-240704)，CC BY-NC 4.0，固定 XF 聲音。每次最多 80 字；不支援的用字會拒絕合成，數字請改成客語讀法。這不是華語自動翻譯，發音尚待母語者驗證。

既有華語使用 Windows 台灣華語；既有台語實驗室使用 Meta MMS 白話字，仍需人工翻譯及核對。不能宣稱公文已能自動轉成正確台語或客語。

先依上述步驟建立主程式 `.venv`，並安裝 Python 3.11 與 uv，再執行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_hakka.ps1
```

此步驟建立獨立 `.venv-local-tts`，下載約 1 GB 上游權重及 CPU 語音套件。初始化需要網路，之後語音合成離線；不占用文件辨識的 GPU。版本清單在 `scripts/hakka-requirements-lock.txt`，模型 revision、授權與 SHA256 在 `MODEL_SOURCES.json` 和 `evaluation/hakka-v1/`。權重與虛擬環境不會上傳 GitHub。


## 台語漢字轉白話字草稿

「台語實驗室」新增漢字輸入，例如「食飽未？」。按「漢字轉白話字草稿」，核對讀音後即可試聽。若對應文件，仍須由台語使用者先翻譯並確認與原文意思相符；轉寫不等於華語翻譯。每次 80 個漢字，未知字、外文和阿拉伯數字會拒絕處理，數字請先改為讀法。

更新套件：`.venv/Scripts/python.exe -m pip install -r requirements.txt`。新增依賴為 Taibun 1.1.8 / msgpack 1.1.2，台語聲音使用原有 MMS 模型，無需下載另一個大型模型。首次台語模型載入較久；後續短句測試約 0.3–0.6 秒，不代表其他文件或設備的速度。

Taibun 程式 MIT，字詞資料依套件聲明為 CC BY-SA 4.0；Meta 聲音模型 CC BY-NC 4.0。鼻音上標的模型輸入轉換、實測限制與來源見 `evaluation/taigi-hanji-v1/README.md`。台語及客語發音均尚待母語者驗證。
