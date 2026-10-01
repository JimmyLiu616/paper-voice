# ASR 非語音前置檢查

2026-10-02：正式採用相同 VAD 設定的前置檢查，避免沒有語音的錄音先載入 Taiwan Tongues ASR CE 模型才回報未辨識到問題。沒有更新權重、調整 VAD 門檻或改寫問題文字。

## 實測

每筆各執行一個全新 Python 子程序，包裝後仍呼叫真正的 WhisperModel 建構子來計數，使用真實模型推論。先跑完整基準，再跑候選，沒有清空檔案系統快取。

| 輸入 | 原版／新版模型載入次數 | 原版程序秒數 | 新版程序秒數 |
|---|---:|---:|---:|
| 靜音 | 0 / 0 | 0.473 | 0.513 |
| 點擊聲 | 1 / 0 | 12.380 | 0.578 |
| 440 Hz 純音 | 1 / 0 | 8.972 | 0.579 |
| 固定亂數白雜音 | 1 / 0 | 8.151 | 0.573 |
| 合成期限問題 | 1 / 1 | 15.637 | 15.402 |
| 合成文件問題 | 1 / 1 | 15.501 | 16.085 |
| 文件問題音量乘 0.1 | 1 / 1 | 15.753 | 15.917 |
| 期限問題前後各加一秒靜音 | 1 / 1 | 16.416 | 16.062 |

四筆非語音的拒絕訊息均相同；四筆合成語音的 text、raw_text、language、duration 均相同。這只支持這批訊號的載入成本改善，語音轉寫並非一致變快，不能宣稱一般延遲或真人／台語／客語辨識品質改善。每個情境只有一組觀察，沒有統計顯著性結論。

正式 HTTP API 也已驗證：點擊聲、白雜音返回 422，分別約 0.694／0.582 秒；合成文件問題返回 200，文字「我需要準備什麼文件」，約 15.530 秒。完整資料見 [live-api.json](live-api.json)。

## 修改與驗證

音訊仍先受原有長度、解碼及音量檢查。之後使用 faster-whisper 1.2.1 原本 transcribe 路徑相同的 `VadOptions(min_silence_duration_ms=500)`；沒有找到語音就沿用原拒絕訊息。有語音則以原始音訊與原設定轉寫，保留原轉寫中的 VAD。這會在有語音時重複一次小型 VAD；本輪不改切段方式以免混入另一項變動。

新增六項測試涵蓋前置拒絕、靜音、解碼失敗，以及中文／英文／自動語言與 beam 設定原樣保留。完整 Python 回歸 183 項通過，有一項既有 Starlette/httpx 棄用提示。前端未修改，沿用上輪 JavaScript 22 項結果。

原始配對紀錄：[baseline-results.jsonl](baseline-results.jsonl)、[candidate-results.jsonl](candidate-results.jsonl)、[comparison.json](comparison.json)。輸入雜湊、範圍與門檻見 [plan.json](plan.json)，舊版程式保留於 [baseline-worker.py](baseline-worker.py)。只有自製合成問題文字，沒有真人聲音、上傳文件或模型權重。

## 重跑

在 Windows 完成專案及指定 ASR 模型安裝、啟動本機服務後，以尚未建立 `.runtime/asr-preflight-v1` 的工作副本執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\benchmark_asr_preflight.py --prepare
.\.venv\Scripts\python.exe -X utf8 scripts\benchmark_asr_preflight.py --variant baseline
.\.venv\Scripts\python.exe -X utf8 scripts\benchmark_asr_preflight.py --variant candidate
```

prepare 使用隨附舊版作為基準、當前 worker 作為候選，缺少兩筆測試音檔時呼叫本機 Windows TTS 產生。新設備的語音或套件版本可能不同，請比較新生成 plan 的音檔雜湊，不能把新結果當成原始輸入的精確重現。已存在的結果目錄不會覆寫。

實测後只改善 runner 的準備步驟，加入基準快照及自動合成缺少的音檔；量測邏輯不變。當時使用的 runner 雜湊保存於 comparison。本輪也更正舊 asr-validation.json 四筆合成測試的 metrics.scope，原先通用輔助函式誤稱 human-corrected；原文字、時間與數值未修改。
