# 紙聲通：老師展示包

下載頁：https://github.com/JimmyLiu616/paper-voice/releases/tag/v0.1.0-demo

- `paper-voice-demo.mp4`：真實本機操作畫面剪輯，含 Windows 合成中文旁白及畫面字幕。
- `paper-voice-demo.srt`：另附段落字幕。
- `paper-voice-submission.zip`：原始碼、原創範例、測試與安裝說明。
- `paper-voice-smoke-001-adapter.zip`：4.7 MB LoRA 增量權重及授權、版本、驗證報告；ZIP 約 2.5 MB。
- `SHA256SUMS.txt`：下載檔案雜湊。

## 影片實際展示

選取原創虛構补件通知，啟動圖片辨識，查看期限、應備文件、費用與例外條件，展開來源引文及辨識原文，播放中文朗讀，執行有依據問答與無資料拒答，再以上傳合成音檔示範 Taiwan Tongues ASR CE → 核對文字 → 文件問答。台語示範限於白話字試聽功能。

影片由當次實際操作的瀏覽器擷取畫面剪輯，包含定格、段落切換及等待省略，**不是連續螢幕錄影，不呈現即時處理速度**。旁白及中文回答範例透過本機 Windows TTS 另行合成；ASR 輸入片段使用實際上傳的合成測試音檔，不是現場真人麥克風。畫面沒有替換模型答案。

本次圖片辨識 44.8 秒，ASR 16.84 秒。這些是此設備與此範例的單次觀察，不是一般效能保證。

## 如實展示的限制

- 例外條件卡夾帶重複的費用文字，仍須核對。
- 「最晚什麼時候要完成」的初次答案只有「下午5時前」，日期只在引文中；追問完整日期時間後才完整回覆。
- 引文對應不能保證辨識或語意正確。影片不是準確率評測。
- 此次未實測實體相機、真人麥克風或台語口音品質。
- 台語功能不自動翻譯公文；未由代理勾選人工核對或資料授權。
- 正式服務使用原版 Gemma 3；附帶 LoRA 只有單一合成範例的一次 optimizer step，未部署、沒有任務品質改善證據。

## 給老師展示的方式

先播放 MP4；若要現場操作，完成 README 安裝後執行 `Start.cmd`，開啟 http://127.0.0.1:8765 。模型初次下載／載入需時間，可在上課前完成。模型從官方來源取得，版號及授權見 `MODEL_SOURCES.json`。實驗 adapter 的下載與載入方法見 [ADAPTER_RELEASE.md](https://github.com/JimmyLiu616/paper-voice/blob/main/training/ADAPTER_RELEASE.md)。

這是可重建的展示原型，發布不等於競賽報名完成。
