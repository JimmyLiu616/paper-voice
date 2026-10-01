# 首次具核對聲明的文件任務微調

2026-10-02完成 `notices-reviewed-001`。這次確實訓練了文字理解adapter，與較早單筆smoke流程不同；候選在開發集新增錯誤拒答，因此未採用、未部署，也未執行保留測試推論。

## 資料與分組

從本機核對頁保存12份已確認匯出，每份都有核對者、時間、逐份內容確認及授權聲明。軟體只能記錄這些聲明，不能證明核對者身分或審閱深度。文件、欄位及36題問答與公開原創草稿相同，沒有內容修改；原始匯出及核對者資訊僅存 `training/data/`，不公開。

原始分組8 train／4 dev沒有test。在首次任務訓練前，從4份dev中保留「地方檔案影本寄送確認」與英文「Community fridge label collection」作test；其餘2份仍為dev，形成 **8 train／2 dev／2 test**。只在實驗副本調整split，沒有改文件、標籤、核對聲明或瀏覽器暫存。分組與雜湊見 `../evaluation/document-lora/notices-reviewed-001/partition.json`。

這是同一批AI原創、使用者確認的合成通知，並非來自不同機構的真實公文。test內容在撰寫及核對時可見，未用來生成評測、更新權重或選擇本次adapter；不能稱為盲測或真實世界獨立測試。前述兩份文件只曾參與格式／tokenizer檢查，沒有舊模型任務評測紀錄。

## 訓練與驗證

- 原生 `mistralai/Ministral-3-3B-Instruct-2512-BF16`，固定revision `b6d637bef2393152b3da2b2fde72eecdee30557e`；NF4／BF16、rank-4 LoRA，只更新語言注意力q/v。
- 1 epoch，32個訓練任務（每份四欄擷取及3題問答），batch 1、梯度累積4、learning rate 0.0001、seed 42，共8次optimizer更新。
- 訓練序列271–421 tokens，開發序列282–407 tokens，沒有截斷；最大輸出512 tokens。保留test文字與答案未寫入訓練輸入包。
- 104個adapter張量有變化，顯存保留峰值4,565,499,904 bytes（約4.25 GiB）。各步loss是不同小批次，不用首末loss直接宣稱品質提升。
- 同程序保存與重載後生成8個dev任務；再於全新程序逐一驗證104個張量相同，8筆生成亦完全相同（時間除外）。adapter SHA256為 `c055da2ab0cd7604471990f798a0eb5b0d3a1787addacc8bffcbab9a7e58f9b7`，權重只留本機。

## 結果與決定

| 指標 | 原生Ministral（adapter停用） | 訓練後adapter |
|---|---:|---:|
| 純JSON輸出 | 0/8 | 6/8 |
| 結構可解析（含額外圍欄解析診斷） | 8/8 | 8/8 |
| EOS結束 | 8/8 | 8/8 |
| 四欄精確參考匹配 | 1/8 | 1/8 |
| 有明確答案卻拒答 | 0/6問答 | 1/6問答 |

嚴格整題參考匹配都是0/8，但同義改寫也會失敗，不能稱為語意正確率0%。逐題檢視發現：候補資格題的虛構第二段引文消失，回答更簡短；同時「通知禁止複製錄音」卻被答成found=false，違反不新增否定／例外退步的採用條件。文件清單仍有漏項。完整生成、機械指標及Codex代理審閱見 `../evaluation/document-lora/notices-reviewed-001/`；不是独立人工輸出審查。

**不採用本候選。** 正式服務仍是Gemma，這次沒有與Gemma作同條件比較，不能推論adapter優於正式模型。test保留未推論，不以test反覆挑選超參數。下一步可在新的train素材補強「明確禁止／例外可回答」與「真的未提供」的對照，dev／test原題不得挪入train。

## 重現入口

需使用本機保存且經聲明的分組檔。避免覆寫原實驗，重跑應使用新名稱：

```powershell
.\.venv-train\Scripts\python.exe -X utf8 scripts\train_document_lora.py training\data\notices-reviewed-001\train.jsonl training\data\notices-reviewed-001\dev.jsonl training\data\notices-reviewed-001\test.jsonl --name notices-reviewed-002 --epochs 1 --accumulation 4 --learning-rate 0.0001 --max-tokens 1024 --max-new-tokens 512 --seed 42
.\.venv\Scripts\python.exe -X utf8 scripts\score_document_lora.py --name notices-reviewed-002
.\.venv-train\Scripts\python.exe -X utf8 scripts\verify_document_lora.py --name notices-reviewed-002
```

這些命令不部署、不公開核對者資訊、不更新已發布smoke權重。公開草稿仍維持未確認狀態；他人需自行審查，不能冒用本機核對者聲明。
