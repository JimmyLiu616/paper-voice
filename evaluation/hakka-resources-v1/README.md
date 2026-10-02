# 全本機客語翻譯資源查核

查核日期：2026-10-02。狀態：找到可申請之訓練語料，尚未取得授權語料、啟動客語微調或部署新翻譯模型。使用者選擇先準備申請資料。

後續補查找到前次遺漏的 OmniTranslate 1.1 公開多語翻譯權重，包含 `hak` 標籤與 GGUF 版本。已下載 Q8_0 並完成本機診斷；正確 `hak_Hani` 代碼的中文／英文輸入仍出現錯誤字串、重複及生成中止，未部署。詳見[實測紀錄](../hakka-omnitranslate-v1/README.md)。不應將本報告解讀成「完全沒有公開客語翻譯候選」。

## 可行的下一步

[臺灣主權 AI 訓練語料庫：客語能力認證初級詞彙](https://taic.moda.gov.tw/datasets/3c152762-101f-4a52-be38-d2094b9efd8f)由客家委員會提供，標示僅授權 AI 訓練使用，適用[臺灣主權 AI 訓練語料授權條款第 1 版](https://taic.moda.gov.tw/content/license)。[申請頁](https://taic.moda.gov.tw/member)要求基本資料、申請用途、預期效益及 PDF 佐證文件；使用者目前沒有通過審核的帳號。

已在本機準備專案佐證 PDF 與可貼入申請欄位的文字，尚未提交申請。附件說明使用現有 Ministral 3 3B 與 QLoRA 做小規模中文轉客語研究。是否取得完整平行例句、實際腔調範圍及授權期限須以核准下載內容為準。訓練後品質仍需實測。

## 查核結果

| 來源 | 查得內容 | 本次採用狀態 |
| --- | --- | --- |
| [ngocthien/hakka-translation-model](https://huggingface.co/ngocthien/hakka-translation-model) 與 hakka_translation_pinyin | 前次查核匿名存取 HTTP 401，無可用權重下載 | 未下載；不推斷是私人或已刪除 |
| [Ayaka/MoeDict-cmn-hak-10k](https://huggingface.co/datasets/Ayaka/MoeDict-cmn-hak-10k) | 10,723 筆；有 mandarin/hakka 欄位，但資料卡未聲明授權及完整原始來源 | 未用於訓練；公開可讀不等於已核對訓練權利 |
| [formospeech/hakka_elearning](https://huggingface.co/datasets/formospeech/hakka_elearning) | metadata 顯示 15,797 筆四縣資料，有 hanzi/mandarin；README 匿名存取 401 | 僅查 metadata |
| [formospeech/hakka_elearning_example_clean](https://huggingface.co/datasets/formospeech/hakka_elearning_example_clean) | metadata 有四縣 2,759、海陸 5,055 筆；網站要求同意存取條件 | 未申請或下載受限資料 |
| [formospeech/hakka_certification_example](https://huggingface.co/datasets/formospeech/hakka_certification_example) | metadata 有四縣 2,755、海陸 5,046 筆；README 匿名存取 401 | 僅查 metadata |
| [formospeech/hakkadict_moe_example](https://huggingface.co/datasets/formospeech/hakkadict_moe_example) | metadata 有中文與客語欄位；README 匿名存取 401 | 未取得授權或下載 |
| [舊客委會開放辭彙](https://data.gov.tw/dataset/119175) | 標示政府資料開放授權條款，但資料集已下架 | 非現成下載來源 |
| [GoHakka](https://gohakka.org/copyright) | 雖標示 CC BY-SA，另明示作為 AI 主要訓練數據需書面許可 | 不作為本次語料來源 |

HF metadata 固定版本：Ayaka `0ff3934145a4b4c20997b04be896a9c10cd701f5`；elearning `d225948588bfbc6e2a2f307273527aa536b33b8e`；clean `78378773f9e01854afb74fc33c4186b6f8e77e93`；certification `d263cc1613962e1e78c3090588f979dd8f293cdd`；moe_example `d02bae11589417ba8b73e690cd465614e124cc30`。筆數為資料庫宣告，不代表已檢查所有對齊或可供訓練的筆數。

另一個可申請來源為[客委會公告的客華平行辭庫](https://www.hakka.gov.tw/chhakka/app/data/view?id=25&module=hotnews&serno=47548)，由 ACLCLP 辦理；與本次 TAIC 申請分開，尚未申請、付款或簽署協議。

## 已完成的本機文字預檢

從[官方公開教材下載頁](https://elearning.hakka.gov.tw/hakka/download-files)下載 115 年初級四縣及海陸兩個小型 ODS。這是教材格式預檢，**不視為已取得 TAIC 訓練授權，也不保證與 TAIC 提供版本相同**。原始教材與整理結果只保存在被排除發布的 `.runtime`，未納入 GitHub 或繳交 ZIP。

| 腔調 | 含雙語例句的儲存格配對數 | 原檔位元組 | SHA-256 |
| --- | ---: | ---: | --- |
| 四縣 | 817 | 112,339 | `720ead8e40f43b9cfaa96ba3c210b28d6aa6927296e672f54ec87cbb5fd7bdcc` |
| 海陸 | 817 | 68,350 | `429385867159cf304e0257d444c1ba69abcade908266bdb1ef6adf93abec3181` |

共 1,634 個儲存格配對、819 種不同中文儲存格內容，其中 312 個客語儲存格有變體記號，365 個配對包含多行。數量不是獨立句數；保留整格內容，未任意拆句、去括號或補譯文。每筆保留來源 URL、腔調、詞條編號、原始檔雜湊及 `training_authorized: false`。

## 取得授權後的評測設計

1. 依核准原檔重新整理，不以本次預檢教材替代；保存授權證明、期限、版本和檔案雜湊。
2. 以來源詞條及標準化中文重複句建立跨腔連通分組；整組切分 train/dev/test。異體、多行配對先明確處理，不能將近似例句跨分割。
3. 先固定保留測試集；測試句不作提示範例、檢索資料或訓練目標。起始小樣本規模視實際合格資料量決定。
4. 比較句型方法、未微調模型、QLoRA 模型；報告 chrF、數字及單位保留、條件與否定錯誤、缺漏、延遲及 GPU 用量。指標與條件檢查不能證明母語自然度。
5. 另建公文／生活通知測試，避免把教材詞彙分數宣稱成公文準確率。尚無客語標準答案的案例只能作功能觀察，不能報翻譯正確率。
6. 不以「成功訓練」作為上線條件。依實際結果決定是否接入翻譯朗讀；推論流程仍維持自動，語言品質評測不等同每次操作要求人工核對。

本次未更改應用程式客語翻譯行為；目前仍使用已支援句型及獨立的本機客語 TTS。
