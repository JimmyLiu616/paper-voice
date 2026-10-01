# 本機 QLoRA 可行性檢查

這個實驗只回答：本機是否能在量化模型上完成反向傳播、更新 LoRA 權重、保存及重載。它不是公文任務訓練，也不驗證辨識／問答品質。正式服務仍使用 Gemma；實驗 adapter 不自動部署。

## 可重現設定

- 基礎模型：`mistralai/Ministral-3-3B-Instruct-2512-BF16`，Apache-2.0。
- 固定 revision：`b6d637bef2393152b3da2b2fde72eecdee30557e`。
- 原生權重與 tokenizer 共13個檔案，下載器核對大小及 LFS SHA256；smoke runner 再核對全部檔案 SHA256。沒有下載重複的 consolidated 格式，也不執行 remote code。
- 環境：獨立 `.venv-train`，Python 3.11；套件版本見 `requirements-cuda.txt`，完整解析結果見安裝後產生的 `requirements-cuda-lock.txt`。
- 模型載入：4-bit NF4、double quant、BF16 compute、SDPA。完整 VLM 載入，但只有語言注意力的 q/v projections 加 LoRA；視覺部分凍結，輸入不含圖片。
- LoRA：r=4、alpha=8、dropout=0；batch=1；最大256 tokens，超過就停止而不截斷；只對 assistant 回覆計算 loss。
- AdamW：lr=0.0001、weight_decay=0、梯度範數上限1、seed=42，一個 optimizer step。
- 資料：`smoke-fixture.json`，一筆新編虛構通知，`human_reviewed=false`；不是正式 train/dev/test，也不取自既有評測。

## 執行

先用 Python 3.11 建立 `.venv-train`，在專案目錄執行：

```powershell
uv --cache-dir .runtime/uv-cache pip install --python .venv-train/Scripts/python.exe --index-url https://download.pytorch.org/whl/cu128 torch==2.10.0
uv --cache-dir .runtime/uv-cache pip install --python .venv-train/Scripts/python.exe -r training/requirements-cuda-lock.txt
.venv/Scripts/python.exe -X utf8 scripts/download_training_model.py
.venv-train/Scripts/python.exe -X utf8 scripts/training_preflight.py --environment training
.venv-train/Scripts/python.exe -X utf8 scripts/train_lora_smoke.py --name smoke-001
.venv-train/Scripts/python.exe -X utf8 scripts/verify_lora_smoke.py --name smoke-001
```

原生權重約7.7GB，另需環境、下載快取與執行空間。執行前確認 GPU 沒有其他模型佔用；8GB 顯卡的單批可行性須以實測為準，不由推論容量推估。

每次使用新 run 名稱，結果保存在 `.runtime/training-runs/<name>/`，不覆寫舊結果。失敗也留下 traceback、階段與當時設定。目錄包含腳本與輸入快照、執行報告及成功時的 adapter；權重和環境排除在 Git／提交 ZIP 外。

通過條件包含有限 loss／梯度、非零梯度、adapter 參數確實改變、序列化檔案有效，及重新載入後 loss 與儲存前相差不超過0.0001。loss 是同一筆訓練樣本上的檢查，不能用來宣稱泛化改善。實測摘要以 `lora-smoke-report.json` 為準；檔案尚未產生時代表未完成這項驗證。

## 2026-10-01 實測結果

`smoke-001` 已通過，另由 `verify_lora_smoke.py` 在新的 Python 程序重新載入基礎模型及 adapter，再次重現相同 loss。

| 項目 | 實測 |
|---|---:|
| GPU | RTX 5060 Laptop，8GB |
| 輸入長度／計算 loss 的回覆 tokens | 109／14 |
| LoRA 可訓練參數 | 1,171,456 |
| optimizer steps | 1 |
| 有限梯度張量／實際變動張量 | 104／52 |
| 同一訓練樣本 loss，更新前 → 後 | 1.764758 → 1.583132 |
| 獨立程序的原模型／adapter loss | 1.764758／1.583132 |
| PyTorch 顯存配置／保留峰值 | 3.92／3.99 GiB |
| adapter 檔案大小 | 4,701,064 bytes |
| 執行時間（含檔案雜湊、載入、訓練及同程序重載） | 42.88秒 |
| 獨立程序重載驗證時間 | 17.33秒 |

顯存數字不包含桌面等其他程序的占用。只有短文字的一個批次，不能外推為長公文或圖片 LoRA 的顯存需求。標準 LoRA 初始化中 B 矩陣為零，第一步只更新52個 B 張量是預期現象；已確認其餘基礎權重不在 optimizer 參數中。

完整摘要保存設定、套件版本、資料／腳本／模型與 adapter 雜湊；原始報告與4.7MB adapter 位於 `.runtime/training-runs/smoke-001/`。本次未執行公文品質評估，未將這個 adapter 加入正式服務。PEFT 儲存時曾提示離線狀態未取得遠端 config；本次未變更字彙表，保存了104個 adapter 張量，後續獨立程序驗證成功。

安裝時遇到大型 wheel 傳輸緩慢，已用 `scripts/download_training_wheels.py` 從官方 PyPI 分段下載並核對完整 SHA256，再以本機 wheel 及原快取完成離線安裝。55個已安裝套件通過 `uv pip check`；此下載工具只適用所列 Windows／Python 3.11 版本，其他平台應用一般安裝方式。

訓練程序結束後，已用正式服務對既有 `dev-registration` 標準文字完成欄位擷取及費用問答，回覆「新臺幣250元」並附原文，耗時12.84秒；服務仍是原 Gemma 與原 app.py。此檢查只確認環境隔離後服務可運行，不是新的品質基準。

後續有效微調仍須不同來源的 train/dev/test、人工複核、相同推論條件下的原模型／adapter 對照，以及期限、金額、否定、例外與錯誤自信回答的逐例判讀。原本公文與合成回歸分數不能拿來當此 adapter 的成績。

## 官方依據

- [模型卡](https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512-BF16)
- [Transformers 模型載入](https://huggingface.co/docs/transformers/model_doc/ministral3)
- [PEFT 量化訓練](https://huggingface.co/docs/peft/developer_guides/quantization)
- [bitsandbytes 安裝與硬體支援](https://huggingface.co/docs/bitsandbytes/installation)
