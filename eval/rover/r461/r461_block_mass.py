#!/usr/bin/env python3
# R461: 逐块量注入体量 (只读实发 full-*.json; 不重建 prompt)
import glob, json, re, sys, collections

def blocks(msg):
    """按已知标记切段: [本轮参考上下文]/[下轮预估]/[SessionMemory]/[承接状态#### *]"""
    idx = []
    for m in re.finditer(r'\[(本轮参考上下文|下轮预估[^\]]*|SessionMemory[^\]]*|承接状态[^\]]*|完成|Memory \(RAG\)|长期记忆[^\]]*)\]', msg):
        idx.append((m.start(), m.group(1)))
    out = collections.OrderedDict()
    for i, (pos, name) in enumerate(idx):
        end = idx[i+1][0] if i+1 < len(idx) else len(msg)
        out.setdefault(name, 0)
        out[name] = max(out[name], end - pos)
    return out

files = sorted(glob.glob('/tmp/r460_env/logs/adapter/full-*.json'))
print('files=%d' % len(files))
agg = collections.OrderedDict()
for f in files:
    try:
        msgs = json.load(open(f, encoding='utf-8'))
    except Exception as e:
        print('VOID', f, e); continue
    if not isinstance(msgs, list): continue
    users = [m for m in msgs if m.get('role') == 'user']
    if not users: continue
    last = users[-1]['content']
    b = blocks(last)
    tag = f.split('full-')[1].replace('.json', '')
    print(tag, 'total=%d' % len(last), {k: v for k, v in b.items()})
    for k, v in b.items():
        agg[k] = agg.get(k, 0) + v
print('--- sums ---')
for k, v in agg.items(): print(k, v)
