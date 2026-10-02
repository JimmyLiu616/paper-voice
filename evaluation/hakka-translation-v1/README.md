# 中文通知短句 → 客語草稿 → 本機語音

使用者選擇尚未申請官方 API，先完成本機展示版。此版採限定整句的規則轉換，不使用客語翻譯 LLM，不是任意中文通用翻譯。四縣、海陸共用文字草稿，由既有 VoxHakka 模型選腔。母語者自然度、變調及數字讀法尚未驗證。

## 候選翻譯失敗與部署選擇

`plan.json` 是模型測試前固定的6句及2腔。`probe.jsonl` 保留 Gemma 3 4B 的12筆輸出：例如把身分證改為個人證／證件，並將應申請的期限句改成「毋使……申請」。數字未變不代表語意正確，故不採用。

`sarc-probe.jsonl` 是既有 SARC 台語12B模型的6句四縣指令測試，仍出現台語詞彙與數字單位缺漏，故不採用。`rejected_llm_prompt.py` 保留當時提示及保護方式，正式客語端點完全不載入它。未改動正式台語模型或文件模型。

正式 `scripts/hakka_translation.py` 僅對完整支援句型轉換，不截掉未知的後半句。涵蓋應備文件、期限、免費、年齡費率、紙本限制及已辦免再辦；數字及文件名稱保留，特殊數字拒絕猜讀。這是人工撰寫的轉換規則；成功匹配不等於獨立翻譯品質得分。對未知句型不能刪掉例外來繞過檢查。

## 實際測試

- `rule-pronunciation.json`：6句及2句補充案例，共8句×2腔，發音字典沒有未知字。這只代表字典覆蓋，並非語音品質。
- 第一個完整句子合成因模型沒有句號 token 而回422；在 worker 將句末、列表與分句標點映成模型支援的逗號停頓，保留所有文字。
- `live-audio.json`：正式本機 API 產生免費活動與期限各2腔，共4個有效22050Hz單聲道WAV。合成端到端約20.6–21.5秒，音檔約3.7–6.5秒。單次觀察、無母語者聽辨。音檔只存本機，不上傳模型權重。
- 真實瀏覽器確認中文範例可轉換；「本活動免費，但材料費另收。」整段拒絕並清掉舊草稿；未核對會拒絕播放。照片辨識後的期限可带入並轉換，`workspace.png` 保留未勾選核對框的畫面。該次照片24.9秒，與CPU語音測試並行，不作新速度結論。
- 音檔技術測試走獨立客語試聽端點，沒有冒充使用者提交人工確認。獨立試聽的UI播放器另行驗證。草稿朗讀端點由測試確認未核對、非法來源及失效文件均會拒絕。
- 278項Python與41項JavaScript測試通過。包含否定／額外條件不會被截掉、文件來源綁定、確認、過期結果不覆蓋新文字及標點停頓。

重跑音檔檢查：啟動本機應用後執行 `python scripts/evaluate_hakka_translation.py`。該腳本不會提交人工核對聲明。

## 來源與後續

沿用 [VoxHakka模型](https://huggingface.co/formospeech/yourtts-htia-240704)（CC BY-NC 4.0）與 [FormoSpeech G2P](https://github.com/hungshinlee/formospeech-g2p)。版本及模型雜湊見 MODEL_SOURCES.json 與 evaluation/hakka-v1。

用詞參照[客委會線上華客翻譯](https://speech.hakka.gov.tw/Translation/Online)的自製短句查詢，並非人工審定。查詢用的是自製測試句，正式本機應用沒有連接此服務。官方亦提供需申請的[客華雙向翻譯 API](https://www.hakka.gov.tw/chhakka/app/data/view?id=25&module=hotnews&serno=e049eaed-e159-4cb3-b0b4-72289ab37f18)；目前尚未整合，不能把規則版宣稱成官方翻譯。
