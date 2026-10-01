"""Create original fictional document fixtures, not scanned personal documents."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
font_file = 'C:/Windows/Fonts/msjh.ttc'
regular = ImageFont.truetype(font_file, 32)
title = ImageFont.truetype(font_file, 48)
small = ImageFont.truetype(font_file, 23)
samples = {
    'notice': {'title': '安心社區服務站｜補件通知', 'lines': [
        '本文件為虛構展示範例，非正式公文。', '',
        '發文日期：民國115年10月1日',
        '主旨：社區關懷活動報名資料補件', '',
        '您的報名資料尚缺文件，請於期限前補交。',
        '補件期限：民國115年10月20日下午5時前',
        '應備文件：身分證影本、填妥的報名表',
        '辦理地點：安心社區服務站一樓櫃台',
        '服務時間：週一至週五，上午9時至下午5時',
        '費用：免費', '',
        '如已完成補件，請忽略本通知。',
        '未載明的事項，請向服務站確認。',
    ]},
    'event': {'title':'和樂社區｜手機攝影體驗', 'lines':[
        '本文件為虛構展示範例，非正式公告。', '',
        '活動日期：2026年10月18日',
        '活動時間：上午10時至中午12時',
        '活動地點：和樂活動中心二樓教室', '',
        '報名截止：2026年10月12日下午5時',
        '參加對象：年滿60歲的社區居民',
        '請攜帶：已充電的智慧型手機、老花眼鏡',
        '報名費用：新臺幣100元',
        '報名方式：請到活動中心服務櫃台登記', '',
        '名額有限，額滿即停止受理。',
        'Community Photography Workshop',
    ]}
}
for name, sample in samples.items():
    image=Image.new('RGB',(1100,1400),'white')
    d=ImageDraw.Draw(image)
    d.rectangle((0,0,1100,16),fill='#17675b')
    d.text((65,85),sample['title'],font=title,fill='#17383b')
    d.line((65,168,1035,168),fill='#b9cac8',width=2)
    y=205
    for idx,line in enumerate(sample['lines']):
        d.text((70,y),line,font=small if idx==0 else regular,fill='#687b7d' if idx==0 else '#222d31')
        y+=65
    d.line((65,1250,1035,1250),fill='#dce4e3',width=2)
    d.text((70,1280),'紙聲通 PAPER VOICE / 原創測試資料 / 2026',font=small,fill='#637a7c')
    image.save(ROOT/'samples'/f'{name}.png')
    (ROOT/'samples'/f'{name}.txt').write_text(sample['title']+'\n'+'\n'.join(sample['lines']),encoding='utf-8')
(ROOT/'samples'/'README.txt').write_text('這些文件由專案自製，所有機構、事件與通知均為虛構，僅作展示與功能測試。可依專案 MIT 授權使用。',encoding='utf-8')
print('Created 2 original document images and text references.')
