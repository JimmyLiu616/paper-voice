# 文件理解 LoRA 實驗入口

`scripts/train_document_lora.py` 將已核對的文件資料接到獨立 Ministral 3 3B 文字 QLoRA 實驗。它不變更紙聲通正式模型、不部署、不上傳權重。

目前驗證到資料門檻、CPU optimizer 迴圈及生成輸入邊界；**完整 CUDA 任務訓練尚未執行**。既有 `smoke-001` 使用另一個單批程式，不能當成本入口已完整跑通的證據。12份實際草稿仍未人工核對，也缺少獨立 test。

## 先確認資料

依 `REVIEW_WORKFLOW.md` 準備人工核對的 train／dev／test JSONL。三組必須有不同來源與模板家族；test 不可使用已看過並調參的案例。各列需保留核對者、帶時區的日期、方法及權利聲明。檢查器只能檢查聲明和結構，不能證明語意或授權有效。

在專案根目錄執行：

```powershell
.\.venv-train\Scripts\python.exe -X utf8 scripts\train_document_lora.py training\data\train.jsonl training\data\dev.jsonl training\data\test.jsonl --name notices-001 --check-only
```

此步驟不載入模型、不建立輸出目錄、不啟動 GPU。未核對或缺任一組會以退出碼1拒絕。`eligible=true` 只表示資料結構與聲明通過；不是完成 tokenization、GPU 容量或品質驗證。

## 執行受控實驗

先完成 `LORA_SMOKE.md` 所述獨立 CUDA 環境與官方固定版號 checkpoint。執行前確認顯存可用；本程式不會自動關閉其他服務或模型。

```powershell
.\.venv-train\Scripts\python.exe -X utf8 scripts\train_document_lora.py training\data\train.jsonl training\data\dev.jsonl training\data\test.jsonl --name notices-001 --epochs 1 --accumulation 4 --learning-rate 0.0001 --max-tokens 1024 --max-new-tokens 512 --seed 42
```

流程：

1. 重新驗證原始資料，建立只含 train／dev 的輸入快照與分組雜湊；test 內容與答案不寫入輸出。
2. 逐檔驗證固定原生 checkpoint 的大小／SHA256。离線使用 tokenizer，檢查 assistant-only loss mask、EOS、序列上限；不截斷。
3. 載入 NF4／BF16 模型，只開放語言注意力 q／v 的 rank-4 LoRA，關閉 adapter 先生成全部 dev 題目答案。
4. 以 batch size 1、每4例累積一次梯度訓練。例子等權，每輪依固定種子重排；不足4例的尾批依實際筆數平均。非有限 loss／梯度立即中止。
5. 確認 adapter 有有限且非零變化，保存 safetensors，再於同程序重載該 adapter，以相同 dev 問題、greedy 設定及輸出上限生成比較答案。
6. 保存原始生成文字、reference、問題雜湊、EOS是否結束、生成時間、各步 loss、顯存峰值與程式／模型／輸出雜湊。生成時只帶 user token prefix，不餵 reference。

输出位於 `.runtime/document-training/notices-001/`；同名目錄不覆寫，中斷或失敗的資料夾保留供追查，另用新名稱重跑。輸出可能包含經授權但非公開的文件內容，預設排除 Git 與交件 ZIP。

## 如何判斷是否值得採用

`baseline-dev.jsonl` 是同一原生 Ministral checkpoint 關閉 adapter 的答案；`adapter-dev.jsonl` 是已保存並重載的 adapter 答案。**這不是與正式 Gemma 服務的等價比較**，也不是正式 API 的完整輸出格式。

對照每個 `source_id`／`task`，逐題檢查日期與上午／下午、金額、應備文件、否定、對象與例外，以及引文是否真正支持答案。輸出未以 EOS 結束可能截斷，不能當正確。不要只看平均 loss 或 JSON 是否能解析。

訓練跑完只標示 `completed-awaiting-quality-review`，`task_quality_verified` 和 `deployed` 保持 false。新入口尚未有完整 CUDA 實跑與獨立程序重載驗證；取得資料後需補做。先依 dev 固定候選，再另執行保留 test；本程式不提供最終 test 推論，不會自動讀取 test 答案來挑選 adapter。未通過 `EXPERIMENT_PLAN.md` 的日期／金額／否定條件門檻，就保留正式原模型。

## 本輪驗證

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_document_trainer.py tests\test_training_messages.py tests\test_training_tokens.py -q
```

25項通過：實際12份未審核草稿從訓練入口被拒絕；隔離假聲明只用來驗證資料閘門，不作訓練素材；CPU toy model 驗證權重更新、尾批平均與非有限 loss 停止；受控生成器確認不將參考答案放進輸入。這些都不是 GPU 任務成效或人工審核完成的證據。

另執行完整 Python 回歸91項通過，保留既有 Starlette／httpx 棄用警告。正式命令列再送入12份實際草稿，退出碼1，沒有建立訓練輸出目錄、沒有 optimizer step；摘要見 `evaluation/qa-completeness/document-trainer-v1.json`。
