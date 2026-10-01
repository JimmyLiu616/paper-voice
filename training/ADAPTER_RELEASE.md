---
license: apache-2.0
base_model: mistralai/Ministral-3-3B-Instruct-2512-BF16
library_name: peft
language:
- zh
tags:
- lora
- experimental
---

# Paper Voice smoke-001：單步 LoRA 實驗權重

此 adapter 是一個合成通知樣本、一次 optimizer step 的 QLoRA 流程驗證。它不是完成公文任務微調的模型，沒有未見資料品質成績，也沒有載入紙聲通正式服務。紙聲通的示範影片使用原版 Gemma 3，不使用此 adapter。

下載：[GitHub 示範版發布頁](https://github.com/JimmyLiu616/paper-voice/releases/tag/v0.1.0-demo)。`paper-voice-smoke-001-adapter.zip` 包含 adapter、設定、授權、合成訓練範例、驗證報告與 SHA256 清單；不含數 GB 的基底模型。

## 模型與修改

- 基底：`mistralai/Ministral-3-3B-Instruct-2512-BF16`。
- 固定 revision：`b6d637bef2393152b3da2b2fde72eecdee30557e`。
- 基底來源：https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512-BF16
- 修改：Paper Voice 專案以原創虛構通知訓練一次；僅保存語言模型 q/v attention 的 LoRA 增量權重，r=4、alpha=8、dropout=0。
- 4-bit NF4 double quantization、BF16 計算，RTX 5060 Laptop 8GB。
- adapter：4,701,064 bytes；SHA256 `fd5cf52f668d3ea7bd21663802d7da7c749811ceb666243dd77bc62fa299beab`。
- 授權：本發布的 adapter 採 Apache-2.0；保留 Mistral 基底來源及授權副本。應用程式自己的 MIT 授權不取代模型授權。

## 已驗證與限制

同一訓練樣本 loss 從 1.764758 降至 1.583132；獨立程序重載可重現。這只表示權重更新、保存及載入有效，不表示公文辨識或問答品質改善。沒有正式 train/dev/test 品質比較。不能把此實驗稱為已完成視覺模型微調；此步驟僅用短文字。

## 載入示例

使用與應用分開的訓練環境，套件版本見 `training/requirements-cuda-lock.txt`，配置說明見 `training/LORA_SMOKE.md`。解壓下載包到自己的目錄，以下把 `ADAPTER_DIRECTORY` 改成其中含 `adapter_config.json` 的資料夾。

```python
import torch
from transformers import BitsAndBytesConfig, Mistral3ForConditionalGeneration
from peft import PeftModel, prepare_model_for_kbit_training

base = Mistral3ForConditionalGeneration.from_pretrained(
    "mistralai/Ministral-3-3B-Instruct-2512-BF16",
    revision="b6d637bef2393152b3da2b2fde72eecdee30557e",
    trust_remote_code=False,
    device_map={"": 0},
    dtype=torch.bfloat16,
    attn_implementation="sdpa",
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    ),
)
base = prepare_model_for_kbit_training(base, use_gradient_checkpointing=False)
model = PeftModel.from_pretrained(base, "ADAPTER_DIRECTORY", is_trainable=False)
model.eval()
```

首次下載基底需網路與足夠磁碟空間。上述是載入示例；本專案實際執行過的重載與 loss 比對流程見 `scripts/verify_lora_smoke.py` 及包內 `fresh-process-verification.json`。不需安裝此 adapter 即可執行紙聲通。

## 原版應用模型取得

在紙聲通已建立的應用環境執行：

```powershell
ollama pull gemma3:4b
.\.venv\Scripts\python.exe scripts\download_asr.py
.\.venv\Scripts\python.exe scripts\download_taigi.py
```

ASR、MMS 下載腳本固定 revision；Gemma 的 Ollama tag 可能更新，請比對 `MODEL_SOURCES.json` 的 digest。Windows 中文語音由使用者的 Windows 提供，不包含在模型包中。各模型保留其原本授權。
