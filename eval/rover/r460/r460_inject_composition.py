#!/usr/bin/env python3
# R460: 逐轮注入块的**组成拆解** (从我方实发请求的 tail_messages 还原; 只统计块长, 不猜内容)
import json, io, glob, os, re

fs = sorted(glob.glob('/tmp/r458_env/logs/adapter/side-agent-*.json'))
print('=== 每调用: 末条 user 消息长度 + 方括号块分解 ===')
tot_last = 0
for k, f in enumerate(fs, 1):
    d = json.load(io.open(f, encoding='utf-8'))
    ur = d['request'].get('upstream_request', {})
    msgs = ur.get('tail_messages', [])
    if not msgs:
        continue
    last = [m for m in msgs if m.get('role') == 'user']
    if not last:
        continue
    m = last[-1]
    ln = m.get('len', 0)
    head = m.get('head') or ''
    blocks = re.findall(r'\[([^\]]{2,40})\]', head)
    tot_last += ln
    print(f'#{k:2d} last_user_len={ln:5d} blocks={blocks}')
print('末条 user 总长', tot_last, '≈ tok', tot_last // 3)

print()
print('=== 我方 vs codex 每调用均价 ===')
def stat(pat, label):
    ps, cs, gs = [], [], []
    for f in sorted(glob.glob(pat)):
        d = json.load(io.open(f, encoding='utf-8'))
        u = (d.get('response') or {}).get('usage') or {}
        if not u: continue
        ps.append(u.get('prompt_tokens') or 0)
        cs.append(u.get('prompt_cache_hit_tokens') or (u.get('prompt_tokens_details') or {}).get('cached_tokens') or 0)
        gs.append(u.get('completion_tokens') or 0)
    n = len(ps)
    if not n: print(label, 'n/a'); return
    print(f'{label}: n={n} prompt均价={sum(ps)/n:.0f} miss均价={(sum(ps)-sum(cs))/n:.0f} '
          f'gen均价={sum(gs)/n:.0f} hit={100*sum(cs)/sum(ps):.1f}% 稳态hit={100*sum(cs[1:])/max(1,sum(ps[1:])):.1f}%')
stat('/tmp/r458_env/logs/adapter/side-agent-*.json', 'R458 我方')
stat('/tmp/r455_env/logs/adapter/side-codex-*.json', 'codex 冻结')
