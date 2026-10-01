# 文件理解 LoRA 實驗入口

**2026-10-02更新：** 本機核對頁已有12份逐份確認聲明，已保存原始匯出並固定8 train／2 dev／2 test，完成首次32任務LoRA與新程序重載。候選新增否定題拒答，未採用；test未推論。詳見 [REVIEWED_RUN_001.md](REVIEWED_RUN_001.md)。公開隨附草稿仍保持未確認，以下「未核對／待訓練」記述為較早流程或公開草稿狀態，不能用來描述本機這次實驗。

`scripts/train_document_lora.py` 將已核對的文件資料接到獨立 Ministral 3 3B 文字 QLoRA 實驗。它不變更紙聲通正式模型、不部署、不上傳權重。

目前已驗證資料門檻、CPU optimizer 迴圈及生成輸入邊界，並以固定合成素材完成共用 CUDA 流程與獨立程序重載。**人工核對資料的正式任務訓練尚未執行**。這次 `cuda-smoke-document-001` 實際呼叫本入口的共用 runtime，與較早使用另一支單批程式的 `smoke-001` 不同。12份實際草稿仍未人工核對，也缺少獨立 test。

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

正式資料訓練跑完只標示 `completed-awaiting-quality-review`，`task_quality_verified` 和 `deployed` 保持 false。合成流程雖已跑通，正式資料的長度／顯存及任務品質仍須另驗證。先依 dev 固定候選，再另執行保留 test；本程式不提供最終 test 推論，不會自動讀取 test 答案來挑選 adapter。未通過 `EXPERIMENT_PLAN.md` 的日期／金額／否定條件門檻，就保留正式原模型。

## 離線比較已保存的 dev 答案

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\score_document_lora.py --name cuda-smoke-document-001
# 正式訓練完成後，改成該次實驗名稱，例如 notices-001。
```

此命令只讀取已完成實驗的輸入與生成檔，先核對訓練報告記錄的檔案SHA256，再以來源／任務鍵對齊原模型與adapter。問題、reference或文件雜湊不一致、缺題、重複題、非dev輸入皆拒絕。它不匯入GPU套件、不重新生成、不讀test答案，也不改原訓練報告。輸出 `paired-dev-metrics.json`，已存在就停止，不覆寫歷史結果。

- 格式：嚴格JSON、鍵與型別、EOS是否結束。Markdown圍欄只作額外解析診斷，不算嚴格格式通過；重複JSON鍵與非標準常數拒絕。
- 四欄：逐欄與reference精確比對，以及非空值是否為來源片段。只做NFKC與空白正規化，不移除否定、數字或標點。
- 問答：found是否一致、預期無答案卻答有答案、預期有答案卻拒答、答案／引文與reference比對、引文是否在原文。
- 前後對照：新增／失去的嚴格參考匹配及完全相同的生成數量。格式不合法的題不能因未算到「錯誤肯定」就當作答對。

`strict_reference_pass`只是「格式、EOS、來源片段及參考字串皆匹配」，不是語意正確率。有效同義改寫可能失敗；原文引文可能與問題無關，即使來源匹配仍須人工檢查。報告永遠保留 `task_quality_verified=false`、`deployed=false` 與人工複核提示，不把dev分數當部署核准。

2026-10-02實測既有 `cuda-smoke-document-001`：1題前後输出相同，皆以EOS結束，皆有Markdown圍欄，嚴格JSON及參考匹配都是0/1；只在額外解析中可看見found一致、引文存在於原文。仍是同一合成素材兼train／dev，沒有改善或泛化證據。公開報告見 `../evaluation/qa-completeness/cuda-smoke-document-001/paired-dev-metrics.json`。本輪18項新增比較／對齊測試及完整135項Python測試通過，沒有再訓練。

## 本輪驗證

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_document_trainer.py tests\test_training_messages.py tests\test_training_tokens.py -q
```

25項通過：實際12份未審核草稿從訓練入口被拒絕；隔離假聲明只用來驗證資料閘門，不作訓練素材；CPU toy model 驗證權重更新、尾批平均與非有限 loss 停止；受控生成器確認不將參考答案放進輸入。這些都不是 GPU 任務成效或人工審核完成的證據。

另執行完整 Python 回歸91項通過，保留既有 Starlette／httpx 棄用警告。正式命令列再送入12份實際草稿，退出碼1，沒有建立訓練輸出目錄、沒有 optimizer step；摘要見 `evaluation/qa-completeness/document-trainer-v1.json`。

## 共用 CUDA 流程與全新程序重載

```powershell
.\.venv-train\Scripts\python.exe -X utf8 scripts\validate_document_trainer_cuda.py --name cuda-smoke-document-001
.\.venv-train\Scripts\python.exe -X utf8 scripts\verify_document_lora.py --name cuda-smoke-document-001
```

第一個命令僅接受原有 `training/smoke-fixture.json` 的固定內容雜湊，不接受任意資料檔或偽造的已核對狀態。它使用與正式入口相同的 tokenization、模型載入、生成、optimizer、保存與重載程式；train／dev 明確使用同一筆未審核合成通知，狀態為 `completed-synthetic-flow-only`，不走正式資料審核聲明，也不修改12份草稿。第二個命令在全新程序驗證模型／輸入／adapter雜湊，逐張量比對保存與載入的權重，再重現生成文字；也可用於後續正式實驗。

2026-10-01 實跑：229 tokens、1步optimizer、52個adapter張量更新、顯存保留峰值4.02 GiB；原模型與adapter皆生成67 tokens並以EOS結束，答案完全相同。全新程序載入的104個張量逐一完全相符，生成文字及相關記錄也一致（時間除外）。兩個答案仍帶 Markdown JSON 圍欄，不能當成已符合所有格式要求。這是流程與序列化證據，沒有任務品質改善或泛化結論。229-token 顯存不代表1024-token或圖像訓練容量。

追加後完整 Python 回歸97項通過。可公開的完整生成、執行報告及代理審閱位於 `evaluation/qa-completeness/cuda-smoke-document-001/`；其中程式快照只用來追溯版本，執行請使用專案 `scripts/` 的入口。新adapter僅留於本機 `.runtime/document-training/`，未替換正式模型或既有release權重。
