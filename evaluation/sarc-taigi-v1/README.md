# SARC 台語模型載入試驗（尚未部署）

候選為 [SARC-Taigi-LLM-12b](https://huggingface.co/Speech-AI-Research-Center/SARC-Taigi-LLM-12b) 的 LoRA adapter，搭配 [Unsloth Gemma 3 12B 4bit](https://huggingface.co/unsloth/gemma-3-12b-it-bnb-4bit)。固定版本及逐檔雜湊見 `download-manifest.json`；大型 LFS 檔案皆依上游 SHA256 核對。權重僅留在本機，未上傳本程式庫。

16 GB RAM／8 GB GPU 電腦，在卸載正式 Ollama 模型後，嘗試 GPU 6 GiB、CPU 5 GiB 自動分配。首次非同步權重載入 MemoryError；改為循序載入後 Windows 回報分頁檔不足（1455）。尚未完成載入或產生任何翻譯，不能評估這個候選的品質，也不能認定它在所有相同規格電腦都無法運行。

未修改作業系統分頁檔，已恢復正式 Gemma 3 4B。下一步可研究更省記憶體的文字模型載入／量化格式；目前不把此候選列為已完成的台語翻譯功能。SARC adapter 需搭配基礎模型並遵循其授權；下載成功不等於允許任意重新散布。
