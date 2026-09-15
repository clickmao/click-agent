#!/usr/bin/env python3
# R458 判分 —— 只读落盘证据。预注册判据见 docs/plans/v0.78.0-r458-humanized-continuation.md:
#   A1 产物 4/4 不回退; A2 T5 接地(含真实产物名 + 问句, 且无示例菜单 "(如:")  A3 T6 无内部术语 + first.txt 落地
#   A4 [承接状态 v1] 块内文件名 ⊆ 磁盘真实文件; A7 调用数 ≤ 15
import glob, json, os, re, time

AD = os.environ.get('R458_AD', '/tmp/r458_env/logs/adapter')
OURS = '/tmp/r458_env/agent/work'
CODEX = '/tmp/r455_env/codex/work'
TURNS = '/tmp/r458_env/logs/agent-turns.jsonl'
AUDIT = '/tmp/r458_env/logs/audit/action_loop.jsonl'
EXPECT = {'count.txt': '4', 'merged.txt': 'ALPHA\nBETA\nGAMMA', 'stats.txt': 'chars=14', 'first.txt': 'R455 fixture note'}
JARGON = ['可选范围', '检查点', '作废', '槽位', '落不到']
PRISTINE = ['a.py', 'b.py', 'c.py', 'd.py', 'notes.md', 'x.txt', 'y.txt', 'z.txt']


def norm(s):
    return (s or '').strip().replace('\r\n', '\n')


def products(root):
    out = {}
    for k, exp in EXPECT.items():
        p = os.path.join(root, k)
        got = open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else None
        out[k] = {'exists': got is not None, 'ok': got is not None and norm(got) == norm(exp), 'value': norm(got)}
    return out


def our_calls():
    rows = []
    for p in sorted(glob.glob(os.path.join(AD, 'side-agent-*.json'))):
        d = json.load(open(p, encoding='utf-8'))
        req, resp = d.get('request') or {}, d.get('response') or {}
        up = req.get('upstream_request') or {}
        u = resp.get('usage') or {}
        ch = (resp.get('choices') or [{}])[0]
        msg = ch.get('message') or {}
        rows.append({'file': os.path.basename(p),
                     'tools_n': req.get('tools_n') or len(up.get('tools') or []),
                     'msgs_n': req.get('n_messages') or len(up.get('messages') or []),
                     'in': u.get('prompt_tokens') or 0,
                     'cached': u.get('prompt_cache_hit_tokens') or 0,
                     'out': u.get('completion_tokens') or 0,
                     'finish': ch.get('finish_reason'),
                     'tool_calls': len(resp.get('tool_calls') or msg.get('tool_calls') or []),
                     'brief_block': '[承接状态 v1]' in json.dumps(up, ensure_ascii=False)})
    return rows


def brief_telemetry():
    """A4: 承接块的**落地证据**取三处外部真值 —— ① 遥测 continuation_brief（含 total/state, 链自报）
    ② 实发请求里模型对承接项的原话（截断存 head, 只作旁证）③ T5 回复点名的文件与磁盘比对（零编造）。"""
    ev, ts = [], []
    p = '/tmp/r458_env/agent/work/data/telemetry/host.jsonl'
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8-sig'):
            ln = ln.strip()
            if not ln:
                continue
            d = json.loads(ln)
            if d.get('point') in ('continuation_brief', 'continuation_closure'):
                ev.append({'point': d['point'], **(d.get('kv') or {})})
    for f in sorted(glob.glob(os.path.join(AD, 'side-agent-*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        s = json.dumps(d, ensure_ascii=False)
        if '承接状态' in s:
            ts.append(os.path.basename(f))
    return {'events': ev, 'briefs': [e for e in ev if e['point'] == 'continuation_brief'],
            'closures': [e for e in ev if e['point'] == 'continuation_closure'],
            'requests_echoing_brief': ts}


def our_turns():
    if not os.path.exists(TURNS):
        return []
    d = json.load(open(TURNS, encoding='utf-8'))
    ts = d['turns'] if isinstance(d, dict) and 'turns' in d else d
    out = []
    for i, t in enumerate(ts, 1):
        r = t.get('reply') or t.get('content') or ''
        out.append({'turn': i, 'len': len(r), 'text': r})
    return out


def audit_rows():
    out = []
    if os.path.exists(AUDIT):
        for ln in open(AUDIT, encoding='utf-8'):
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except Exception:
                continue
            out.append({'tool': d.get('tool'), 'rc': d.get('rc'), 'args_head': (d.get('args_head') or '')[:90]})
    return out


def main():
    op, cp = products(OURS), products(CODEX)
    calls, turns, aud = our_calls(), our_turns(), audit_rows()
    bf = brief_telemetry()
    agg = {'calls': len(calls), 'in': sum(c['in'] for c in calls), 'cached': sum(c['cached'] for c in calls),
           'out': sum(c['out'] for c in calls), 'tool_steps': sum(1 for c in calls if c['tool_calls'] > 0)}
    t5 = turns[4]['text'] if len(turns) > 4 else ''
    t6 = turns[5]['text'] if len(turns) > 5 else ''
    real_names = [k for k in EXPECT if op[k]['exists']] + PRISTINE
    t5_referenced = sorted({k for k in EXPECT if k in t5})
    a2 = bool(t5_referenced) and ('?' in t5 or '？' in t5) and '(如:' not in t5
    a3_jargon = sorted({w for w in JARGON if w in t6})
    v = {
        'round': 'R458', 'mode': 'humanized_continuation',
        'ours_products': op, 'codex_products_frozen': cp,
        'ours_products_ok': sum(1 for x in op.values() if x['ok']), 'codex_products_ok': sum(1 for x in cp.values() if x['ok']),
        'ours_calls': agg, 'ours_turns': [{'turn': t['turn'], 'len': t['len'], 'head': t['text'][:150].replace('\n', ' ')} for t in turns],
        't5_text': t5, 't6_text': t6,
        'A2_t5_grounded': a2, 'A2_t5_referenced': t5_referenced, 'A2_menu_present': '(如:' in t5,
        'A3_t6_jargon': a3_jargon, 'A3_t6_clean': not a3_jargon,
        'A4_brief': bf,
        'A4_t5_reference_is_real': all(os.path.exists(os.path.join(OURS, n)) for n in t5_referenced),
        'A4_briefs_n': len([e for e in bf['events'] if e.get('point') == 'continuation_brief']),
        'A4_t5_invented_files': sorted({t for t in re.findall(r'[A-Za-z0-9_.\-]+\.[A-Za-z0-9]+', t5)
                                        if t not in os.listdir(OURS)}),
        'audit_rows': aud, 'audit_tools': [r['tool'] for r in aud],
        'codex_frozen': {'calls': 13, 'in': 91002, 'cached': 87936, 'out': 597},
        'r457_frozen': {'products_ok': 4, 'calls': 15},
        'ours_cache_pct': round(100.0 * agg['cached'] / agg['in'], 1) if agg['in'] else None,
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    json.dump(v, open('/home/agentuser/AgentFramework/eval/rover/r458/verdict-r458.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('R458 判决 (人性化承接轮)')
    print(f"  A1 产物 我方 {v['ours_products_ok']}/4 (R457 冻结 4/4) | codex(冻结) {v['codex_products_ok']}/4")
    for k in EXPECT:
        print(f"    {k:11s} 我方={op[k]['value']!r:22s} ok={op[k]['ok']}")
    print(f"  A2 T5 接地={a2} 引用产物={t5_referenced} 示例菜单={'(如:' in t5}")
    print(f"  A3 T6 内部术语={a3_jargon or '无'} 干净={not a3_jargon}")
    print(f"  A4 承接块遥测 {len(bf['briefs'])} 次 {[ (e.get('artifacts'), e.get('total'), e.get('state')) for e in bf['briefs'] ]}")
    print(f"     收口闸 {len(bf['closures'])} 次 {[ e.get('grounded') for e in bf['closures'] ]}; T5 引用名全真={v['A4_t5_reference_is_real']} 编造={v['A4_t5_invented_files'] or '无'}")
    print(f"  A7 调用 {agg['calls']} (R457 冻结 15) 工具步={agg['tool_steps']} in={agg['in']} cached={agg['cached']} ({v['ours_cache_pct']}%) out={agg['out']}")
    print(f"  审计工具行 {len(aud)}: {v['audit_tools']}")
    print('  --- T5 原文 ---')
    print('  ' + t5.replace('\n', '\n  ')[:700])
    print('  --- T6 原文 ---')
    print('  ' + t6.replace('\n', '\n  ')[:700])


if __name__ == '__main__':
    main()
