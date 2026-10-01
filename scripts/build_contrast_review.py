"""Six new unreviewed train-only notices; paired variants must stay in one split."""
import hashlib
import json
from pathlib import Path

try:
    from .build_training_review import make, question
    from .validate_training_data import validate, reserved_evaluation_sources
except ImportError:
    from build_training_review import make, question
    from validate_training_data import validate, reserved_evaluation_sources

ROOT=Path(__file__).resolve().parents[1]


def candidates():
    rows=[]
    def pair(family,title,deadline,documents,amount,conditions,query,answer,other_questions):
        for index,condition in enumerate(conditions):
            paragraphs=['期限：'+deadline,'應備文件：\n'+documents,'費用：\n'+amount,'其他事項：'+condition]
            row=make(f'contrast-{family}-{index+1}','train',title,paragraphs,deadline,documents,amount,condition,
                     [question(query,answer if index==0 else '文件沒有提供這項規定，無法確認。',
                               condition if index==0 else '', 'explicit-rule' if index==0 else 'abstention')]+other_questions)
            row.update(family='contrast-'+family,contrast_pair='contrast-'+family,
                       contrast_role='explicit' if index==0 else 'unspecified',title=title+f' · {index+1}')
            rows.append(row)
    docs='（一）借用申請表正本。\n（二）參與課程證明影本。\n（三）委託辦理者另附委託書及代理人證件正本。'
    fee='每組押金300元；學校團體每組押金100元，完成清點後退還，押金不是租金。'
    pair('observation-equipment','環境觀測器材借用',
         '請於117年3月9日17時前完成借用登記，當日17時後送達者不受理。',docs,fee,
         ['禁止自行拆開器材外殼，故障器材請交回管理員處理。','本次借用僅限環境課程使用。'],
         '借用期間可以自行拆開器材外殼嗎？','不可以；禁止自行拆開外殼，故障器材須交回管理員處理。',[
             question('委託辦理時，需要準備哪些文件？','借用申請表正本、參與課程證明影本，另附委託書及代理人證件正本。',docs,'documents'),
             question('學校團體每組要繳300元再加100元嗎？','不是，學校團體每組押金100元，完成清點後退還；押金不是租金。',fee,'fee')])
    docs='改期確認表及原報名收據影本；委託送件者另附委託書。'
    fee='一般參加者報名費180元。\n持有效志工證者報名費60元，不另收一般費用。\n交通費另計，金額未載。'
    pair('riverside-walk','河岸健走活動改期',
         '請於117年9月12日中午12時前交回改期確認表，以窗口收件時間為準。',docs,fee,
         ['經主辦單位核准因公缺席者退還全額報名費；未經核准者不適用這項退費規定。',
          '缺席名單於活動後彙整，不影響下一場報名資格。'],
         '經核准因公缺席，可以退還全額報名費嗎？','可以，經主辦單位核准因公缺席者可退還全額報名費；未經核准者不適用。',[
             question('委託送件可以只交改期確認表嗎？','不可以，還要原報名收據影本，委託送件另附委託書。',docs,'documents'),
             question('持有效志工證要繳180元再加60元嗎？','不用，報名費為60元，不另收一般費用；交通費另計且金額未載。',fee,'fee')])
    docs='Bring the confirmation email, the materials selection sheet, and a photo ID for inspection. A photocopy of the ID is not required.'
    fee='The workshop fee is NT$240 per person. Students with a valid student card pay NT$90. Materials cost is charged separately, up to NT$80 per person.'
    pair('weaving-workshop','Community weaving workshop',
         'Submit the enrollment form by 15:30 on 20 May 2028. Late forms will not be accepted.',docs,fee,
         ['Participants whose registration is cancelled by the organizer receive a full workshop-fee refund; materials charges are refunded only for unopened kits.',
          'Only participants with confirmed enrollment may attend the session.'],
         '主辦單位取消報名時，工作坊費和已拆封材料費都會全額退嗎？',
         '工作坊費會全額退還，但材料費只有未拆封材料包才退，已拆封不符合這項條件。',[
             question('只帶證件影本就能完成現場查驗嗎？','不可以，須帶確認電子郵件、材料選擇單與附照片證件供查驗；不需證件影本。',docs,'documents'),
             question('持有效學生證的90元費用已包含材料嗎？','沒有，工作坊費為90元，材料另計，每人材料費上限80元。',fee,'fee')])
    return rows


def main():
    rows=candidates()
    errors=validate(rows,*reserved_evaluation_sources())
    structural=[e for e in errors if not e.endswith('rights and human review must be explicitly confirmed')]
    if structural or len(errors)!=len(rows):
        raise ValueError(str(errors))
    payload={'version':'contrast-train-drafts-v1','synthetic':True,'purpose':'Unreviewed train-only contrast pairs. Never use pair siblings as dev/test.','rows':rows}
    data=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    (ROOT/'static/training-review-contrast.json').write_bytes(data)
    report={'rows':len(rows),'pairs':3,'questions':sum(len(r['questions']) for r in rows),
            'splits':{'train':6,'dev':0,'test':0},'structural_errors':structural,
            'approval_errors':errors,'eligible_for_training':False,'sha256':hashlib.sha256(data).hexdigest(),
            'original_review_dataset_modified':False,'original_test_sources_used':False}
    (ROOT/'training/contrast-drafts-validation.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
