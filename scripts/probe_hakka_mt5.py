import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
from pathlib import Path
import argparse, json, time, traceback
import torch, transformers
from transformers import MT5ForConditionalGeneration, T5Tokenizer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation/hakka-mt5-v1'
parser = argparse.ArgumentParser(description='Offline exploratory Hakka mT5 probe; author did not document the task prefix.')
parser.add_argument('--model-dir', required=True, help='Local directory containing the downloaded model and tokenizer')
parser.add_argument('--num-beams', type=int, default=1)
parser.add_argument('--basic-prefixes', action='store_true', help='Only raw input and English Chinese-to-Hakka prefix')
parser.add_argument('--output-name', default='probe.json')
args = parser.parse_args()
MODEL = str(Path(args.model_dir).resolve())
PREFIXES = ['', 'translate Chinese to Hakka: ', 'translate Mandarin to Hakka: ', 'translate zh to hak: ', '中文轉客語：', '翻譯成客語：']
if args.basic_prefixes: PREFIXES = PREFIXES[:2]
CASES = [
 ('greeting', '你好，謝謝你的幫忙。'),
 ('free', '本活動免費，不必繳費。'),
 ('documents', '請攜帶身分證影本及報名表。'),
 ('deadline', '請在10月15日下午5點以前提出申請，逾期不受理。'),
 ('conditional_fee', '只有65歲以上才免費，其他人須繳500元。'),
 ('done_exception', '已經完成登記的人，不必再提出申請。'),
 ('paper_only', '本次僅接受紙本申請，不接受線上申請。'),
 ('conditional_docs', '如果委託別人辦理，還需要附上委託書。'),
 ('deadline_extension', '如果截止日遇到假日，期限延到下一個上班日。'),
 ('fee_refund', '報名費300元，取消報名不退費。'),
]
report = {'status':'loading', 'model':'qavit/mt5-small-hak', 'revision':'231a3eefac886c436da8301e57f056cac7ff04ba', 'deployed':False, 'native_reviewed':False, 'prompt_format':'Undocumented by author; six exploratory prefixes, not claimed to be official.', 'torch':torch.__version__, 'transformers':transformers.__version__, 'results':[]}
OUT.mkdir(parents=True, exist_ok=True)
def save(): (OUT / args.output_name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
save()
try:
 torch.set_num_threads(4)
 torch.manual_seed(42)
 device = 'cuda' if torch.cuda.is_available() else 'cpu'
 report['device'] = device
 tokenizer = T5Tokenizer.from_pretrained(MODEL, local_files_only=True)
 import sentencepiece as spm
 sp = spm.SentencePieceProcessor(model_proto=(Path(MODEL) / 'spiece.model').read_bytes())
 report['tokenizer_checks'] = [{'source':text, 'matches_native_sentencepiece':tokenizer.encode(text, add_special_tokens=False) == sp.encode(text)} for _, text in CASES]
 model = MT5ForConditionalGeneration.from_pretrained(MODEL, local_files_only=True, torch_dtype=torch.float32).to(device).eval()
 report['status'] = 'running'
 report['decoding'] = {'do_sample':False, 'num_beams':args.num_beams, 'max_new_tokens':96, 'dtype':'float32'}
 save()
 for prefix in PREFIXES:
  for case_id, source in CASES:
   start = time.monotonic()
   inputs = tokenizer(prefix + source, return_tensors='pt').to(device)
   with torch.inference_mode():
    generated = model.generate(**inputs, do_sample=False, num_beams=args.num_beams, max_new_tokens=96)
   raw = tokenizer.decode(generated[0], skip_special_tokens=False)
   output = tokenizer.decode(generated[0], skip_special_tokens=True)
   row = {'id':case_id, 'source':source, 'prefix':prefix, 'output':output, 'raw_output':raw, 'seconds':round(time.monotonic()-start, 3), 'new_tokens':generated.shape[1]-1, 'hit_length_limit':generated.shape[1]-1 >= 96}
   report['results'].append(row)
   save()
   print(json.dumps(row, ensure_ascii=False), flush=True)
 report['status'] = 'complete'
except Exception:
 report['status'] = 'error'
 report['error'] = traceback.format_exc()
 print(report['error'], flush=True)
finally:
 save()
if report['status'] == 'error':
 raise SystemExit(1)
