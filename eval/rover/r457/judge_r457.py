#!/usr/bin/env python3
# R457 判分 —— 只读落盘证据: 我方(动作环 on + 台账回灌 + 不落槽转路径) vs codex(R455 冻结读数)。
# 预注册判据(见 docs/plans/v0.77.0-r457-effect-closure.md):
#   A2 stats.txt 落地且 = chars=14 (R456 为「口算 15 + 无文件」)
#   A3 first.txt 落地且 = R455 fixture note (R456 为「入口作废」吞并)
#   A1 台账行 "[本轮已执行]" 出现在实发回灌(适配器逐请求落盘)
import glob, json, os, time

AD = os.environ.get('R457_AD', '/tmp/r457_env/logs/adapter')
OURS = '/tmp/r457_env/agent/work'
CODEX = '/tmp/r455_env/codex/work'
TURNS = '/tmp/r457_env/logs/agent-turns.jsonl'
AUDIT = '/tmp/r457_env/logs/audit/action_loop.jsonl'
EXPECT = {'count.txt': '4', 'merged.txt': 'ALPHA\nBETA\nGAMMA', 'stats.txt': 'chars=14', 'first.txt': 'R455 fixture note'}


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
                     'tool_calls': len(resp.get('tool_calls') or msg.get('tool_calls') or [])})
    return rows


def ledger_seen():
    """A1: 台账行是否出现在实发回灌(外部真值=适配器落盘的请求体)。"""
    hits, files = 0, []
    for p in sorted(glob.glob(os.path.join(AD, 'side-agent-*.json'))):
        d = json.load(open(p, encoding='utf-8'))
        up = ((d.get('request') or {}).get('upstream_request') or {})
        blob = json.dumps({'tail': up.get('tail_messages'), 'all': up}, ensure_ascii=False)
        if '[本轮已执行]' in blob:
            hits += 1
            files.append(os.path.basename(p))
    return {'hits': hits, 'files': files[:6]}


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
            out.append({'tool': d.get('tool'), 'rc': d.get('rc'), 'args_head': (d.get('args_head') or '')[:90],
                        'effect': (d.get('effect') or '')[:60]})
    return out


def our_turns():
    if not os.path.exists(TURNS):
        return []
    d = json.load(open(TURNS, encoding='utf-8'))
    ts = d['turns'] if isinstance(d, dict) and 'turns' in d else d
    out = []
    for i, t in enumerate(ts, 1):
        r = t.get('reply') or t.get('content') or ''
        out.append({'turn': i, 'len': len(r), 'head': r[:120].replace('\n', ' ')})
    return out


def main():
    op, cp = products(OURS), products(CODEX)
    calls, turns, aud = our_calls(), our_turns(), audit_rows()
    led = ledger_seen()
    agg = {'calls': len(calls), 'in': sum(c['in'] for c in calls), 'cached': sum(c['cached'] for c in calls),
           'out': sum(c['out'] for c in calls), 'tool_steps': sum(1 for c in calls if c['tool_calls'] > 0)}
    v = {
        'round': 'R457', 'mode': 'action_loop_on+ledger+fallthrough',
        'ours_products': op, 'codex_products_frozen': cp,
        'ours_products_ok': sum(1 for x in op.values() if x['ok']), 'codex_products_ok': sum(1 for x in cp.values() if x['ok']),
        'ours_calls': agg, 'ours_turns': turns,
        'ledger_in_replay': led,
        'audit_rows': aud,
        'audit_tools': [r['tool'] for r in aud],
        'codex_frozen': {'calls': 13, 'in': 91002, 'cached': 87936, 'out': 597},
        'ours_cache_pct': round(100.0 * agg['cached'] / agg['in'], 1) if agg['in'] else None,
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    json.dump(v, open('/home/agentuser/AgentFramework/eval/rover/r457/verdict-r457.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('R457 判决')
    print(f"  产物 我方 {v['ours_products_ok']}/4 | codex(冻结) {v['codex_products_ok']}/4")
    for k in EXPECT:
        print(f"    {k:11s} 我方={op[k]['value']!r:22s} ok={op[k]['ok']} | codex={cp[k]['value']!r} ok={cp[k]['ok']}")
    print(f"  我方调用 {agg['calls']} (含工具步 {agg['tool_steps']}) in={agg['in']} cached={agg['cached']} ({v['ours_cache_pct']}%) out={agg['out']}")
    print(f"  A1 台账回灌命中 {led['hits']} 个实发请求 {led['files']}")
    print(f"  审计工具行 {len(aud)}: {v['audit_tools']}")
    for r in aud[:6]:
        print(f"    {r['tool']:12s} rc={r['rc']} args={r['args_head']!r}")
    print(f"  轮次长度 {[t['len'] for t in turns]}")


if __name__ == '__main__':
    main()
