# 台語漢字轉寫與本機試聽

本輪增加台語漢字 → 白話字草稿 → Meta MMS 音檔，減少自行鍵入羅馬字的負擔。不是華語句子翻譯器，不會把尚未翻譯的公文直接宣稱為台語。

採用 [Taibun 1.1.8](https://pypi.org/project/taibun/1.1.8/) 的 POJ、south、字典本調設定。多音字、文白讀、斷詞及變調仍可能不合語境。產生草稿不會勾選人工核對；等待期間若漢字、原文、白話字或文件改變，舊回應不會覆蓋新內容。

## 模型輸入

保留原始白話字讓使用者核對；送入 MMS 前採 NFKC、小寫及明確標點轉空白。NFKC 會把鼻音上標 `ⁿ` 轉成 `n`，保留一個字母，避免 Transformers 的詞表過濾直接刪除它。此選擇參考 [MMS 公開資料正規化預設](https://github.com/facebookresearch/fairseq/blob/main/examples/mms/data_prep/norm_config.py)，**不是確認該模型鼻音或台灣口音正確的證據**。所有非標點符號必須通過實際模型字表；未知漢字、外文與數字不得悄悄消失。

## 實測

`report.json` 包含原創短句的真實 CPU 合成結果與五個拒絕案例：

| 台語漢字 | 轉寫與合成耗時 | 音檔長度 |
|---|---:|---:|
| 你好 | 12.104 秒（首次載入） | 0.624 秒 |
| 食飽未？ | 0.309 秒 | 1.456 秒 |
| 請共身分證影本攑來。 | 0.484 秒 | 2.608 秒 |
| 若是已經辦好，就免閣來。 | 0.564 秒 | 2.992 秒 |

全部產生有效 16 kHz 單聲道波形，未遺漏不支援的字元；數字、未知字及混入外文的五例回傳 422。這是流程與字表覆蓋測試，**沒有母語者評分，不是發音正確率**。測試不含網路傳輸，且只有一次觀測。

重現（先完成主程式及台語模型安裝）：

```powershell
.venv/Scripts/python.exe -X utf8 scripts/evaluate_taigi_pronunciation.py --output .runtime/taigi-hanji-check
```

完整測試通過 Python 224 項、JavaScript 30 項。原始測試音檔保留於本機 `.runtime/taigi-hanji-v1`，未上傳 GitHub。

## 授權與資料來源

Taibun 程式：Andrei Harbachov，MIT，見 `third_party/Taibun-LICENSE.txt`。Taibun 的字詞資料依套件聲明為 CC BY-SA 4.0，來源為經 ChhoeTaigi 收錄的台華線上對照典及 iTaigi 華台對照典；不將詞庫視為本專案 MIT 程式碼。本測試報告中的轉寫資料同樣標示 CC BY-SA 4.0，保留來源與改動說明（轉為 POJ／模型正規化）。

模型仍為 [Meta MMS Chinese, Min Nan](https://huggingface.co/facebook/mms-tts-nan)，CC BY-NC 4.0。沒有重訓或重新散布權重。
