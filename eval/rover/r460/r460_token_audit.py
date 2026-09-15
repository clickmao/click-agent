#!/usr/bin/env python3
# R460: 逐调用 token/缓存取证 (我方 R458 run2 + 历史轮 archive) + 工具回灌体量
import json, io, glob, os

def usage_of(f):
    try:
        d = json.load(io.open(f, encoding='utf-8'))
    except Exception:
        return None
    r = d.get('response') or {}
    u = r.get('usage') or d.get('usage') or {}
    if not u:
        ex = d.get('extra') or {}
        u = ex.get('usage') or {}
    return u or None

def scan(pat, label):
    rows = []
    for f in sorted(glob.glob(pat)):
        u = usage_of(f)
        if not u:
            continue
        p = u.get('prompt_tokens') or 0
        c = u.get('prompt_cache_hit_tokens') or (u.get('prompt_tokens_details') or {}).get('cached_tokens') or 0
        g = u.get('completion_tokens') or 0
        rows.append((os.path.basename(f), p, c, g))
    if not rows:
        print(f'{label}: 无 usage 落盘 ({len(glob.glob(pat))} 文件)')
        return rows
    tot_p = sum(r[1] for r in rows); tot_c = sum(r[2] for r in rows); tot_g = sum(r[3] for r in rows)
    print(f'=== {label}: 调用 {len(rows)} | prompt ∑{tot_p} | cached ∑{tot_c} | miss ∑{tot_p-tot_c} | gen ∑{tot_g} | hit {100*tot_c/max(1,tot_p):.1f}%')
    for i, (n, p, c, g) in enumerate(rows, 1):
        print(f'   #{i:2d} {n}: prompt={p:6d} cached={c:6d} miss={p-c:6d} hit={100*c/max(1,p):5.1f}% gen={g}')
    return rows

scan('/tmp/r458_env/logs/adapter/side-agent-*.json', 'R458 run2 我方')
scan('/tmp/r457_env/logs/adapter/side-agent-*.json', 'R457 我方')
scan('/tmp/r455_env/logs/adapter/side-agent-*.json', 'R455 我方(无动作环)')
scan('/tmp/r455_env/logs/adapter/side-codex-*.json', 'R455 codex(冻结)')

print()
print('=== 工具回灌体量 (R458 run2 action_loop 审计) ===')
f = '/tmp/r458_env/logs/audit/action_loop.jsonl'
if os.path.exists(f):
    lines = [json.loads(l) for l in io.open(f, encoding='utf-8') if l.strip()]
    print('审计行', len(lines))
    tot = 0
    for l in lines:
        out = str(l.get('output') or l.get('result') or '')
        tot += len(out)
        print(f"  {l.get('tool')} rc={l.get('rc')} out_len={len(out)} args={(l.get('args_head') or '')[:60]!r}")
    print('回灌总字符', tot, '≈ tok', tot // 3)
