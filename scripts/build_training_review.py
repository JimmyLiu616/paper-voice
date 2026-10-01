"""Build original, unreviewed training candidates. No training and no approvals.

All notices below are fictional. They are not copied from official documents,
private uploads, or the project's evaluation fixtures. The first batch is 8 train
drafts and 4 dev drafts; no final test set or quality claim is implied.
"""
import hashlib
import json
from pathlib import Path

from validate_training_data import validate, reserved_evaluation_sources

ROOT = Path(__file__).resolve().parents[1]


def question(text, answer, evidence='', focus='comprehension'):
    return {'question':text,'answer':answer,'found':bool(evidence),
            'evidence':[evidence] if evidence else [],'focus':focus}


def make(identifier, split, title, paragraphs, deadline, documents, amount, conditions, questions):
    return {'schema':'paper-voice-understanding-v1','source_id':identifier,'family':identifier,
            'split':split,'title':title,'license':'MIT','rights_confirmed':False,'human_reviewed':False,
            'provenance':'Original fictional notice authored by Codex; labels are drafts, not independently human-reviewed.',
            'synthetic':True,'document':title+'\n【虛構標註素材，不是正式公告】\n'+'\n'.join(paragraphs),
            'fields':{'deadline':deadline,'required_documents':documents,'amount':amount,'conditions':conditions},
            'questions':questions}


def candidates():
    rows=[]
    rows.append(make('draft-oral-history-release','train','街區口述歷史照片使用確認',[
        '照片展示預定於116年8月1日開始。',
        '請於116年7月12日17時前將照片使用同意書送達故事館櫃台，寄出日期不作為收件依據。',
        '需繳交照片使用同意書及照片編號清單；只填清單不算完成授權。',
        '本次確認不收費。',
        '先前已交同意書者仍須補交照片編號清單。'],
        '116年7月12日17時前將照片使用同意書送達故事館櫃台，寄出日期不作為收件依據。',
        '照片使用同意書及照片編號清單；只填清單不算完成授權。','本次確認不收費。',
        '先前已交同意書者仍須補交照片編號清單。',[
        question('7月12日寄出就算準時嗎？','不算，須在7月12日17時前送達櫃台；寄出日期不作為收件依據。','請於116年7月12日17時前將照片使用同意書送達故事館櫃台，寄出日期不作為收件依據。','deadline'),
        question('之前交過同意書，還要交清單嗎？','仍須補交照片編號清單。','先前已交同意書者仍須補交照片編號清單。','exception'),
        question('最多可以提供幾張照片？','文件沒有提供張數上限。',focus='abstention')]))
    rows.append(make('draft-bike-permit-renewal','train','自行車停車證換發須知',[
        '換發期間為116年2月3日至2月20日，每日9時至16時。',
        '本人辦理請出示舊停車證與身分證明正本；委託辦理另附委託書及受託人身分證明正本。',
        '每張換發費為30元；舊證遺失者每張收取80元，不再加收30元。',
        '舊證遺失者以原登記編號替代舊證。'],
        '116年2月3日至2月20日，每日9時至16時。',
        '本人辦理請出示舊停車證與身分證明正本；委託辦理另附委託書及受託人身分證明正本。',
        '每張換發費為30元；舊證遺失者每張收取80元，不再加收30元。',
        '舊證遺失者以原登記編號替代舊證。',[
        question('遺失舊證要繳110元嗎？','不是，遺失舊證每張收80元，不再加收30元。','舊證遺失者每張收取80元，不再加收30元。','fee'),
        question('委託別人時只帶舊證就可以嗎？','不可以，還要身分證明正本，並另附委託書及受託人身分證明正本。','本人辦理請出示舊停車證與身分證明正本；委託辦理另附委託書及受託人身分證明正本。','documents'),
        question('停車證可以在哪些停車場使用？','文件沒有列出適用停車場。',focus='abstention')]))
    rows.append(make('draft-kitchen-deposit','train','共享廚房清潔押金通知',[
        '使用者須在場地使用前一日中午12時前完成押金繳納。',
        '繳納時出示預約確認單即可，無須附身分證影本。',
        '每次使用收取清潔押金600元；檢查合格後全額退還，押金不是場地租金。',
        '公益共煮方案經核准者免收清潔押金，仍須接受離場檢查。'],
        '場地使用前一日中午12時前完成押金繳納。',
        '出示預約確認單即可，無須附身分證影本。',
        '每次使用收取清潔押金600元；檢查合格後全額退還，押金不是場地租金。',
        '公益共煮方案經核准者免收清潔押金，仍須接受離場檢查。',[
        question('核准的公益方案免押金，也免檢查嗎？','免收清潔押金，但仍須接受離場檢查。','公益共煮方案經核准者免收清潔押金，仍須接受離場檢查。','exception'),
        question('需要附身分證影本嗎？','無須附身分證影本，出示預約確認單即可。','繳納時出示預約確認單即可，無須附身分證影本。','documents'),
        question('場地租金也是600元嗎？','文件沒有提供場地租金金額，600元是清潔押金。',focus='abstention')]))
    rows.append(make('draft-rain-barrel-address','train','雨水桶配送地址更正通知',[
        '第一批配送日為116年5月6日。',
        '需更正地址者，請於116年4月28日18時前提交更正表；逾時更正不適用第一批配送。',
        '更正表應附訂單編號，不需重新繳交原申請書。',
        '更正地址不收手續費；本通知未列配送費。',
        '已交付物流的訂單不能依此方式更正地址，應聯繫原受理窗口。'],
        '116年4月28日18時前提交更正表；逾時更正不適用第一批配送。',
        '更正表應附訂單編號，不需重新繳交原申請書。',
        '更正地址不收手續費；本通知未列配送費。',
        '已交付物流的訂單不能依此方式更正地址，應聯繫原受理窗口。',[
        question('更正地址要重新交原申請書嗎？','不需要，更正表應附訂單編號即可。','更正表應附訂單編號，不需重新繳交原申請書。','documents'),
        question('已交付物流，也能用這份更正表改地址嗎？','不能依此方式更正，應聯繫原受理窗口。','已交付物流的訂單不能依此方式更正地址，應聯繫原受理窗口。','exception'),
        question('配送費是多少？','文件沒有提供配送費。',focus='abstention')]))
    rows.append(make('draft-mobile-library-route','train','巡迴書車臨時站點調整',[
        '116年9月14日，巡迴書車的松葉站改設於市場北側廣場，服務時段為14時至16時。',
        '當日竹林站維持原地點與時段。',
        '這是站點異動通知，讀者不必事先回覆，也無須提交申請文件。',
        '持有預約書者仍須等候到書通知；站點異動不代表預約書已可領取。'],
        '', '', '', '持有預約書者仍須等候到書通知；站點異動不代表預約書已可領取。',[
        question('竹林站也改到市場了嗎？','沒有，竹林站維持原地點與時段。','當日竹林站維持原地點與時段。','entity'),
        question('看到站點異動通知就能領預約書嗎？','還不能據此確認，持有預約書者仍須等候到書通知。','持有預約書者仍須等候到書通知；站點異動不代表預約書已可領取。','exception'),
        question('借閱逾期一天要收多少錢？','文件沒有提供逾期收費。',focus='abstention')]))
    rows.append(make('draft-trail-safety-kit','train','步道志工裝備領用',[
        '裝備領用日為116年3月7日，請於當日15時前到服務站簽領。',
        '攜帶志工識別證正本及領用通知；兩者皆須出示。',
        '本次領用免費，遺失後的補發費用另行公告。',
        '曾領取舊款背心者只領安全帽，不再發給新背心。'],
        '116年3月7日，請於當日15時前到服務站簽領。',
        '志工識別證正本及領用通知；兩者皆須出示。',
        '本次領用免費，遺失後的補發費用另行公告。',
        '曾領取舊款背心者只領安全帽，不再發給新背心。',[
        question('識別證和通知擇一就好嗎？','不是，志工識別證正本與領用通知都要出示。','攜帶志工識別證正本及領用通知；兩者皆須出示。','documents'),
        question('已領過舊款背心的人可以再領新背心嗎？','不可以，只領安全帽，不再發給新背心。','曾領取舊款背心者只領安全帽，不再發給新背心。','exception'),
        question('安全帽遺失補發要多少錢？','文件沒有提供補發金額，費用另行公告。',focus='abstention')]))
    rows.append(make('draft-audio-guide-rental','train','Museum audio guide rental',[
        'Return the audio guide to the front desk by 16:45 on the day of rental.',
        'Show the admission ticket and a photo ID. Staff will inspect the ID and return it immediately.',
        'The rental fee is NT$70 per device. Visitors aged 70 or above pay NT$30; admission is charged separately.',
        'A replacement device is available at no extra rental fee if the first device fails during the same visit.'],
        'Return the audio guide to the front desk by 16:45 on the day of rental.',
        'Show the admission ticket and a photo ID. Staff will inspect the ID and return it immediately.',
        'The rental fee is NT$70 per device. Visitors aged 70 or above pay NT$30; admission is charged separately.',
        'A replacement device is available at no extra rental fee if the first device fails during the same visit.',[
        question('70歲的訪客租一台要多少錢？','租借費為新臺幣30元；門票另外收費。','Visitors aged 70 or above pay NT$30; admission is charged separately.','fee'),
        question('證件會被保管到歸還機器嗎？','不會，工作人員檢查證件後會立即歸還。','Staff will inspect the ID and return it immediately.','documents'),
        question('門票多少錢？','文件只說門票另計，沒有提供門票價格。',focus='abstention')]))
    rows.append(make('draft-community-oven-repair','train','社區麵包窯修繕期間使用說明',[
        '116年11月6日至11月9日修繕的是戶外麵包窯；室內料理教室照常開放。',
        '修繕期間禁止使用戶外麵包窯，無須另行申請暫停使用。',
        '已繳戶外麵包窯使用費者全額退費，請於116年11月20日前提交退款表與原繳費收據影本。',
        '室內料理教室的預約不因本次修繕自動取消。'],
        '116年11月20日前提交退款表與原繳費收據影本。',
        '退款表與原繳費收據影本。',
        '已繳戶外麵包窯使用費者全額退費',
        '室內料理教室的預約不因本次修繕自動取消。',[
        question('修繕期間室內料理教室也關閉嗎？','沒有，室內料理教室照常開放。','修繕的是戶外麵包窯；室內料理教室照常開放。','entity'),
        question('申請退款要交收據正本嗎？','通知要求原繳費收據影本，並提交退款表。','請於116年11月20日前提交退款表與原繳費收據影本。','documents'),
        question('修繕廠商是哪一家？','文件沒有提供修繕廠商。',focus='abstention')]))
    rows.append(make('draft-garden-waitlist','dev','社區園圃候補席次確認',[
        '候補序號21至25號獲得本輪確認資格，其他序號請等候後續通知。',
        '取得資格者須在116年1月18日16時前回覆確認，未回覆即放棄本輪席次。',
        '回覆時附候補通知及本人簽名的耕作約定書。',
        '取得席次後每季繳交材料費450元；本次回覆階段不收費。',
        '尚未取得席次者不必先繳材料費。'],
        '取得資格者須在116年1月18日16時前回覆確認，未回覆即放棄本輪席次。',
        '候補通知及本人簽名的耕作約定書。',
        '取得席次後每季繳交材料費450元；本次回覆階段不收費。',
        '尚未取得席次者不必先繳材料費。',[
        question('序號26號這次也要回覆嗎？','本輪確認資格是21至25號，其他序號等候後續通知。','候補序號21至25號獲得本輪確認資格，其他序號請等候後續通知。','eligibility'),
        question('回覆時就要付450元嗎？','不用，本次回覆階段不收費，取得席次後才每季繳450元。','取得席次後每季繳交材料費450元；本次回覆階段不收費。','fee'),
        question('下一輪什麼時候通知？','文件沒有提供下一輪日期。',focus='abstention')]))
    rows.append(make('draft-archive-copy-delivery','dev','地方檔案影本寄送確認',[
        '申請人收到估價單後五個工作日內，請回傳簽名的估價單及寄送地址確認表。',
        '每頁影印費2元，郵資依估價單另外計算；選擇現場領取者免郵資。',
        '未回傳確認表以前不製作影本；已完成付款不代表文件已寄出。'],
        '收到估價單後五個工作日內',
        '簽名的估價單及寄送地址確認表。',
        '每頁影印費2元，郵資依估價單另外計算；選擇現場領取者免郵資。',
        '未回傳確認表以前不製作影本；已完成付款不代表文件已寄出。',[
        question('現場領取是不是連影印費也免了？','不是，現場領取免的是郵資；每頁影印費仍為2元。','每頁影印費2元，郵資依估價單另外計算；選擇現場領取者免郵資。','fee'),
        question('付款完成就代表已寄出嗎？','不代表文件已寄出。','已完成付款不代表文件已寄出。','exception'),
        question('確切要在幾月幾日前回傳？','文件沒有收到估價單的日期，無法換算確切截止日。',focus='abstention')]))
    rows.append(make('draft-nature-recording-access','dev','自然觀察紀錄室開放調整',[
        '116年6月2日起，錄音資料改在二樓聆聽室提供；照片資料仍在一樓閱覽。',
        '聆聽錄音需出示預約確認信，閱覽照片無須預約。',
        '兩項服務皆免費，但不得自行複製錄音檔案。',
        '預約確認信不是錄音檔案複製許可。'],
        '', '聆聽錄音需出示預約確認信，閱覽照片無須預約。',
        '兩項服務皆免費，但不得自行複製錄音檔案。',
        '預約確認信不是錄音檔案複製許可。',[
        question('照片也移到二樓了嗎？','沒有，照片資料仍在一樓閱覽。','錄音資料改在二樓聆聽室提供；照片資料仍在一樓閱覽。','entity'),
        question('有預約信就能複製錄音檔案嗎？','不能據此取得複製許可，通知也禁止自行複製錄音檔案。','兩項服務皆免費，但不得自行複製錄音檔案。','exception'),
        question('每天幾點關門？','文件沒有提供每日關門時間。',focus='abstention')]))
    rows.append(make('draft-community-fridge-labels','dev','Community fridge label collection',[
        'Collect the new food labels between 10:00 and 12:00 on 6 April 2027.',
        'Bring the collection email or its printed copy. A membership card is not required.',
        'Each household receives one pack free of charge. Extra packs cost NT$25 each.',
        'Households that collected a free pack in March may buy extra packs but cannot claim another free pack.'],
        'Collect the new food labels between 10:00 and 12:00 on 6 April 2027.',
        'Bring the collection email or its printed copy. A membership card is not required.',
        'Each household receives one pack free of charge. Extra packs cost NT$25 each.',
        'Households that collected a free pack in March may buy extra packs but cannot claim another free pack.',[
        question('一定要帶會員卡嗎？','不需要會員卡，帶領取通知電子郵件或其列印本即可。','Bring the collection email or its printed copy. A membership card is not required.','documents'),
        question('三月領過免費包，這次還能免費領嗎？','不能再領免費包，但可以購買加購包。','Households that collected a free pack in March may buy extra packs but cannot claim another free pack.','exception'),
        question('一包有幾張標籤？','文件沒有提供每包標籤數量。',focus='abstention')]))
    return rows


def main():
    rows=candidates()
    errors=validate(rows,*reserved_evaluation_sources())
    structural=[e for e in errors if not e.endswith('rights and human review must be explicitly confirmed')]
    if structural:
        raise ValueError('\n'.join(structural))
    assert len(errors)==len(rows) and all(not r['human_reviewed'] and not r['rights_confirmed'] for r in rows)
    payload={'version':'original-review-drafts-v1','synthetic':True,
             'purpose':'Unreviewed training/development candidates, not a completed dataset or holdout test.',
             'rows':rows}
    serialized=json.dumps(payload,ensure_ascii=False,indent=2)+'\n'
    (ROOT/'static/training-review-drafts.json').write_text(serialized,encoding='utf-8')
    report={'version':payload['version'],'rows':len(rows),'questions':sum(len(r['questions']) for r in rows),
            'splits':{s:sum(r['split']==s for r in rows) for s in ['train','dev','test']},
            'structural_errors':structural,'approval_errors':errors,'eligible_for_training':False,
            'sha256':hashlib.sha256(serialized.encode()).hexdigest(),
            'note':'Exact-span and reserved-source checks only; semantic correctness and template independence await human review.'}
    (ROOT/'training/review-drafts-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['rows','questions','splits','structural_errors','eligible_for_training']},ensure_ascii=False))


if __name__=='__main__':main()
