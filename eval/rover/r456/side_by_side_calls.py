#!/usr/bin/env python3
"""两侧统一口径取数（v2，字段按适配器真实 schema）：
冷启动首调用 vs 稳态；逐调用 tools_n/msgs/in/cached/out/tool_calls。
外部真值 = 适配器逐请求落盘（side-*.json）。
"""
import glob, json, os, sys

AD = '/tmp/r455_env/logs/adapter'


def rows(prefix, mark=0.0):
    out = []
    for p in sorted(glob.glob(os.path.join(AD, f'side-{prefix}-*.json')), key=os.path.getmtime):
        if mark and os.path.getmtime(p) < mark:
            continue
        d = json.load(open(p, encoding='utf-8'))
        q, r = d.get('request') or {}, d.get('response') or {}
        u = r.get('usage') or {}
        tcs = r.get('tool_calls') or []
        up = q.get('upstream_request') or {}
        msgs = q.get('n_messages')
        if msgs is None:
            msgs = len(up.get('messages') or [])
        out.append({'f': os.path.basename(p),
                    'tools': q.get('tools_n') or 0,
                    'passed': q.get('passed_tools_n'),
                    'msgs': msgs,
                    'in': u.get('prompt_tokens') or 0,
                    'cached': u.get('prompt_cache_hit_tokens') or 0,
                    'out': u.get('completion_tokens') or 0,
                    'tcs': len(tcs),
                    'text_len': len(r.get('text') or '')})
    return out


def show(tag, rs):
    if not rs:
        print(f'{tag}: 无捕获\n'); return
    print(f'--- {tag}（{len(rs)} 次上游调用，落盘顺序）---')
    print(f"{'#':>2} {'tools':>5} {'msgs':>4} {'in':>7} {'cached':>7} {'hit%':>6} {'out':>4} {'tool_calls':>10} {'text':>5}")
    for i, r in enumerate(rs, 1):
        h = 100.0 * r['cached'] / r['in'] if r['in'] else 0.0
        print(f"{i:>2} {r['tools']:>5} {r['msgs']:>4} {r['in']:>7} {r['cached']:>7} {h:>6.1f} {r['out']:>4} {r['tcs']:>10} {r['text_len']:>5}")
    for name, sub in (('冷启动首调用', rs[:1]), ('稳态 2..n', rs[1:])):
        i_ = sum(r['in'] for r in sub); c_ = sum(r['cached'] for r in sub)
        print(f"  {name:<12} in={i_:>6} cached={c_:>6} ({100.0*c_/i_ if i_ else 0:>5.1f}%) out={sum(r['out'] for r in sub):>4}  调用数={len(sub)}")
    i_, c_ = sum(r['in'] for r in rs), sum(r['cached'] for r in rs)
    print(f"  {'合计':<12} in={i_:>6} cached={c_:>6} ({100.0*c_/i_ if i_ else 0:>5.1f}%) out={sum(r['out'] for r in rs):>4}  调用数={len(rs)}")
    print(f"  tools 声明: {[r['tools'] for r in rs]}  tool_calls 步: {[r['tcs'] for r in rs]}")


mark = float(open('/tmp/r456_env/logs/start.ts').read().strip())
print('=== 我方 click-agent（R456 动作环 on）: 同一适配器/同一 deepseek-flash/同一夹具 ===')
show('我方', rows('agent', mark))
print()
print('=== codex 0.154（冻结读数 R455）: 同一适配器/同一 deepseek-flash/同一夹具 ===')
show('codex', rows('codex'))
