#!/usr/bin/env python3
"""OCRBench 评测（concise 提示，与 MCP vqa_image 一致的口径）。"""
import base64, io, json, os, re, sys, time, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import pyarrow.parquet as pq
from PIL import Image

PARQUET='/root/ocrbench/ocrbench.parquet'
BASE='http://127.0.0.1:8000'
SUFFIX=' Answer with only the answer text, no explanation.'
MAXTOK=64
CONC=2
CKPT='/root/ocrbench/ckpt_concise.json'
OUT='/root/ocrbench/results_concise.json'

def norm(s):
    s=str(s).lower().strip(); s=re.sub(r'[^\w\s\.\-/]',' ',s); s=re.sub(r'\b(a|an|the)\b',' ',s)
    return re.sub(r'\s+',' ',s).strip()
def num_eq(a,b):
    def parse(x):
        x=x.replace(',','').replace(' ','')
        m=re.fullmatch(r'-?\d+(?:\.\d+)?',x); return float(m.group(0)) if m else None
    pa,pb=parse(a),parse(b)
    if pa is None or pb is None: return None
    return abs(pa-pb)<1e-6*max(1,abs(pa),abs(pb))
def score(pred,answers):
    p=norm(pred)
    for a in answers:
        na=norm(a)
        if p==na: return 1
        if num_eq(p,na): return 1
    return 0
def to_b64(im):
    raw=im['bytes'] if isinstance(im,dict) else im
    img=Image.open(io.BytesIO(raw)).convert('RGB')
    if max(img.size)>1024: img.thumbnail((1024,1024), Image.LANCZOS)
    b=io.BytesIO(); img.save(b,'PNG'); return base64.b64encode(b.getvalue()).decode()
def ask(item):
    payload={"model":"local","messages":[{"role":"user","content":[
        {"type":"image_url","image_url":{"url":"data:image/png;base64,"+to_b64(item['image'])}},
        {"type":"text","text":item['question']+SUFFIX}]}],"max_tokens":MAXTOK,"temperature":0,"chat_template_kwargs":{"enable_thinking":False}}
    req=urllib.request.Request(BASE+'/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    r=json.load(urllib.request.urlopen(req,timeout=600))
    txt=r['choices'][0]['message']['content']
    if '</think>' in txt: txt=txt.split('</think>')[-1]
    txt=txt.replace('<think>','').strip()
    return txt.split('\n')[0].strip() if txt else txt

def main():
    limit=int(sys.argv[1]) if len(sys.argv)>1 else 10**9
    items=pq.read_table(PARQUET).to_pylist()
    done={}
    if os.path.exists(CKPT):
        try: done={int(k):v for k,v in json.load(open(CKPT)).items()}
        except Exception: done={}
    todo=[i for i in range(len(items)) if i not in done][:limit]
    t0=time.time()
    def work(i):
        try: return i, ask(items[i])
        except Exception as e: return i, 'ERR:'+repr(e)[:50]
    with ThreadPoolExecutor(max_workers=CONC) as ex:
        for i,pred in ex.map(work,todo):
            done[i]=pred
    json.dump({str(k):v for k,v in done.items()},open(CKPT,'w'))
    rows=[]
    for i,it in enumerate(items):
        if i not in done: continue
        a=it['answer']
        if isinstance(a,str):
            try: a=eval(a)
            except Exception: a=[a]
        rows.append({'i':i,'type':it['question_type'],'dataset':it['dataset'],
                     'question':it['question'],'pred':done[i],'answers':a,'ok':score(done[i],a)})
    acc=100*sum(r['ok'] for r in rows)/len(rows)
    by=defaultdict(lambda:[0,0])
    for r in rows: by[r['type']][0]+=r['ok']; by[r['type']][1]+=1
    print('ACCURACY %.2f n=%d %.0fs'%(acc,len(rows),time.time()-t0),flush=True)
    for k,v in sorted(by.items()): print('  %-42s %6.2f (n=%d)'%(k,100*v[0]/v[1],v[1]),flush=True)
    json.dump({'summary':{'n':len(rows),'accuracy':acc,'by_type':{k:{'acc':100*v[0]/v[1],'n':v[1]} for k,v in by.items()}},'results':rows},open(OUT,'w'),ensure_ascii=False)

main()