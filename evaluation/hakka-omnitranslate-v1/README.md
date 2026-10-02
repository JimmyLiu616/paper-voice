# OmniTranslate 1.1 本機客語探測

日期：2026-10-02。結論：**權重可下載、能本機執行，但本次測試未得到可用的中文轉客語能力，不部署至紙聲通。**

## 權重與執行方式

- 原模型：[MihaiPopa-1/OmniTranslate-1.1](https://huggingface.co/MihaiPopa-1/OmniTranslate-1.1)，0.6B，模型卡標示 Apache-2.0、實驗性。
- 實測：[mradermacher/OmniTranslate-1.1-GGUF](https://huggingface.co/mradermacher/OmniTranslate-1.1-GGUF) 的 Q8_0，639,454,208 bytes。
- 固定 revision：`37b35f67dc9d81daac6a20fdedbdcf4a71d81b0d`。
- 下載後驗證 SHA-256：`f01eca22cffac334b7e944084a10ca9add0a643ae5e67be3ba76cc38e56ff10c`。
- Ollama 0.35.0，CPU 推論，temperature 0、seed 42、context 2048。使用作者文件中的原始 ChatML 提示，包括 `<think>` 前綴。
- 沒有微調、檢索或 few-shot 例句。測試只用專案自建句子；未把使用者文件送至外部服務。

## 測試與結果

`probe.json` 記錄最初 16 次提示探測：8 個中文句子，分別使用 `hak_Hant` 及完整客語／四縣／繁體漢字語言名稱。前者並非後續查到的訓練代碼，故不能單靠這組判定能力。

接著直接核對作者公開 [OmniSurgical 1.0 訓練資料](https://huggingface.co/datasets/MihaiPopa-1/OmniSurgical-1.0)，固定 revision `6950fd8ed0566258fafcb15d3ae88860004597ac` 的 `OmniSurgical_120_Clean.jsonl`，找到實際代碼 `hak_Hani`。該檔只有 5 筆文字包含此精確代碼；這不等於模型全部訓練資料只有 5 筆客語。此次僅唯讀檢查，沒有下載保存或重新發布訓練語料。

`correct-code-probe.json` 記錄使用正確代碼的 6 個客語測試，以及 2 個其他語言對照：

| 輸入 | 結果 |
| --- | --- |
| 中文問候 | 輸出全形拉丁字與西里爾字混合字串，非預期客語漢字 |
| 英文問候 | 輸出西里爾字串，非預期客語漢字 |
| 中文：攜帶身分證影本及報名表 | 重複「扶」直到生成長度上限，未保留文件資訊 |
| 同義英文：攜帶文件 | HTTP 500，`prediction aborted, token repeat limit reached` |
| 中文：65 歲以上免費，其餘繳 500 元 | 同樣觸發 token 重複上限 |
| 同義英文：年齡與費用条件 | 同樣觸發 token 重複上限 |
| 英文問候 → 法文 | 正常返回法文問候，證明該載入／提示路徑能產生合理的其他語言輸出 |
| 英文文件句 → `zho_Hant` | 能產生相關中文，但用了簡體且文件表述不同，不計為通過的繁中翻譯 |

正確代碼的 6 個客語診斷案例均未得到可用輸出。這是少量功能測試，不是正式翻譯準確率，也不能推廣為所有版本或所有提示都必定失敗。英文是人工寫出的診斷輸入，沒有完成自動中文→英文→客語管線。

先前的 HTTP 500 曾使測試中斷；保留兩次中斷記錄，後續補齊各案例錯誤本文，確認是重複 token 限制，並非把伺服器錯誤誤報成正常翻譯。未調高重複上限來掩蓋問題。

## 對產品的決定

不接入自動翻譯與 TTS，沒有將錯誤輸出念成客語來展示。原有受限句型翻譯與本機 VoxHakka 維持原樣。下載權重保留在本機供研究，GitHub 只放紀錄。

已卸載測試模型常駐並恢復 Gemma GPU 預熱。`app-check.json` 記錄實際 `/api/narrate` 回歸檢查：「本活動免費，不必繳費。」經現有句型轉成「這隻活動免費，毋使繳費。」，成功產生 3.669 秒四縣語音，無 speech_error；這是原功能的管線驗證，不是新模型能力或母語品質評分。應用程式 SHA-256 未變。

「可下載且標註客語」已證實；「可靠翻譯臺灣四縣／海陸客語」未證實，且本次診斷有明確反例。一般中文轉客語的完整功能仍未完成。
