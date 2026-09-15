#!/usr/bin/env python3
# R456 判分 —— 只读落盘证据: 我方(动作环 on) vs codex(R455 冻结读数)。
import glob, json, os, time

AD = '/tmp/r455_env/logs/adapter'
OURS = '/tmp/r456_env/agent/work'
CODEX = '/tmp/r455_env/codex/work'
TURNS = '/tmp/r456_env/logs/agent-turns.jsonl'
MARK = '/tmp/r456_env/logs/start.ts'
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
    mark = float(open(MARK).read().strip()) if os.path.exists(MARK) else 0
    rows = []
    for p in sorted(glob.glob(os.path.join(AD, 'side-agent-*.json'))):
        if os.path.getmtime(p) < mark:
            continue
        d = json.load(open(p, encoding='utf-8'))
        req, resp = d.get('request') or {}, d.get('response') or {}
        u = resp.get('usage') or {}
        ch = (resp.get('choices') or [{}])[0]
        msg = ch.get('message') or {}
        rows.append({'file': os.path.basename(p),
                     'tools_n': len(req.get('tools') or []),
                     'msgs_n': len(req.get('messages') or []),
                     'in': u.get('prompt_tokens') or 0,
                     'cached': u.get('prompt_cache_hit_tokens') or 0,
                     'out': u.get('completion_tokens') or 0,
                     'finish': ch.get('finish_reason'),
                     'tool_calls': len(msg.get('tool_calls') or [])})
    return rows


def our_turns():
    if not os.path.exists(TURNS):
        return []
    d = json.load(open(TURNS, encoding='utf-8'))
    ts = d['turns'] if isinstance(d, dict) and 'turns' in d else d
    out = []
    for i, t in enumerate(ts, 1):
        r = t.get('reply') or t.get('content') or ''
        out.append({'turn': i, 'len': len(r), 'ask': ('?' in r or '？' in r),
                    'claim_done': ('已完成' in r or '已写入' in r), 'head': r[:90].replace('\n', ' ')})
    return out


def main():
    op, cp = products(OURS), products(CODEX)
    calls, turns = our_calls(), our_turns()
    agg = {'calls': len(calls), 'in': sum(c['in'] for c in calls), 'cached': sum(c['cached'] for c in calls),
           'out': sum(c['out'] for c in calls), 'tool_steps': sum(1 for c in calls if c['tool_calls'] > 0)}
    v = {
        'round': 'R456', 'mode': 'action_loop_on',
        'ours_products': op, 'codex_products_frozen': cp,
        'ours_products_ok': sum(1 for x in op.values() if x['ok']), 'codex_products_ok': sum(1 for x in cp.values() if x['ok']),
        'ours_calls': agg, 'ours_turns': turns,
        'ours_ask_like': sum(1 for t in turns if t['ask']),
        'codex_frozen': {'calls': 13, 'in': 91002, 'cached': 87936, 'out': 597,
                         'cache_pct': round(100.0 * 87936 / 91002, 1)},
        'ours_cache_pct': round(100.0 * agg['cached'] / agg['in'], 1) if agg['in'] else None,
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    json.dump(v, open('/home/agentuser/AgentFramework/eval/rover/r456/verdict-r456.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('R456 判决')
    print(f"  产物 我方 {v['ours_products_ok']}/4 | codex(冻结) {v['codex_products_ok']}/4")
    for k in EXPECT:
        print(f"    {k:11s} 我方={op[k]['value']!r:22s} ok={op[k]['ok']} | codex={cp[k]['value']!r} ok={cp[k]['ok']}")
    print(f"  我方调用 {agg['calls']} (含工具步 {agg['tool_steps']}) in={agg['in']} cached={agg['cached']} ({v['ours_cache_pct']}%) out={agg['out']}")
    print(f"  codex(冻结) 调用 13 in=91002 cached=87936 (96.6%) out=597")
    print(f"  我方轮内问询 {v['ours_ask_like']}/{len(turns)} | 轮次长度 {[t['len'] for t in turns]}")


if __name__ == '__main__':
    main()
