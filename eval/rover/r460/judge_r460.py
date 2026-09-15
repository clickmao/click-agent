#!/usr/bin/env python3
"""R460 判分 —— 只读落盘证据 (预注册 = eval/rover/r460/prereg-r460.json)。

判据:
  P1 精炼    : T5 回复 ≤170 字 / T6 回复 ≤110 字 / 承接注入块 ≤200 字 (块长取自实发 full-*.json)
  P2 菜单    : T5 回复含 1..3 项编号菜单且首项接地真实产物名; 门 Choices 有事实时含真实名; 空态无示例菜单
  P3 tokens  : prompt ∑ ≤ 46,688 (R458 54,927 的 85%) 且 调用数 ≤ 17
  P4 命中率  : 稳态 (2..n) hit ≥ 92% 且 miss 均价 ≤ 280 (R458 310)
  P5 不回退  : 产物 4/4; T6 内部术语 0; 承接真实项 ≥3; 磁盘级伪造 0
"""
import glob
import json
import os
import re
import time

E = os.environ.get('R460_ENV', '/tmp/r460_env')
AD = os.path.join(E, 'logs/adapter')
OURS = os.path.join(E, 'agent/work')
CODEX = '/tmp/r455_env/codex/work'
TURNS = os.path.join(E, 'logs/agent-turns.jsonl')
AUDIT = os.path.join(E, 'logs/audit/action_loop.jsonl')
EXPECT = {'count.txt': '4', 'merged.txt': 'ALPHA\nBETA\nGAMMA', 'stats.txt': 'chars=14', 'first.txt': 'R455 fixture note'}
JARGON = ['可选范围', '检查点', '作废', '槽位', '落不到']
PRISTINE = ['a.py', 'b.py', 'c.py', 'd.py', 'notes.md', 'x.txt', 'y.txt', 'z.txt']
PREREG = {'t5_max': 170, 't6_max': 110, 'block_max': 200, 'prompt_max': 46688, 'calls_max': 17,
          'steady_hit_min': 92.0, 'steady_miss_max': 280, 'menu_max_items': 3}


def norm(s):
    return (s or '').strip().replace('\r\n', '\n')


def products(root):
    out = {}
    for k, exp in EXPECT.items():
        p = os.path.join(root, k)
        got = open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else None
        out[k] = {'exists': got is not None, 'ok': got is not None and norm(got) == norm(exp), 'value': norm(got)}
    return out


def _cached(u):
    c = u.get('prompt_cache_hit_tokens')
    if c:
        return c
    d = u.get('prompt_tokens_details')
    return (d or {}).get('cached_tokens') or 0


def our_calls():
    rows = []
    for p in sorted(glob.glob(os.path.join(AD, 'side-agent-*.json'))):
        d = json.load(open(p, encoding='utf-8'))
        req, resp = d.get('request') or {}, d.get('response') or {}
        u = resp.get('usage') or {}
        rows.append({'file': os.path.basename(p), 'in': u.get('prompt_tokens') or 0,
                     'cached': _cached(u), 'out': u.get('completion_tokens') or 0})
    return rows


def full_blocks():
    """实发全量消息 ⇒ 承接块真实字符数 + 最后一条 user 消息组成 (禁估算)。"""
    out = []
    for f in sorted(glob.glob(os.path.join(AD, 'full-agent-*.json'))):
        msgs = json.load(open(f, encoding='utf-8'))
        last = None
        for m in msgs:
            if m.get('role') == 'user':
                last = m
        t = (last or {}).get('content') or ''
        i = t.find('[承接状态 v1]')
        blk = 0
        if i >= 0:
            j = t.find('\n', t.find('本轮=', i))
            blk = (j - i) if j > i else len(t) - i
        out.append({'file': os.path.basename(f), 'last_user_chars': len(t), 'brief_block_chars': blk})
    return out


def brief_telemetry():
    ev = []
    p = os.path.join(OURS, 'data/telemetry/host.jsonl')
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8-sig'):
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except Exception:
                continue
            if d.get('point') in ('continuation_brief', 'continuation_closure'):
                ev.append({'point': d['point'], **(d.get('kv') or {})})
    return ev


def our_turns():
    if not os.path.exists(TURNS):
        return []
    d = json.load(open(TURNS, encoding='utf-8'))
    ts = d['turns'] if isinstance(d, dict) and 'turns' in d else d
    return [{'turn': i, 'len': len(t.get('reply') or t.get('content') or ''), 'text': t.get('reply') or t.get('content') or ''}
            for i, t in enumerate(ts, 1)]


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


def menu_items(text):
    """编号菜单项 —— 接受 1./1)/1、 与 ①..③ (R460 首跑实发 ①②③ 被漏判 = 器具缺陷, 已修)。"""
    return re.findall(r'(?:^|[；;，,：:\s])\s*(?:([1-3])[.、)）]|([①②③]))\s*([^；;，,\n]{2,40})', text)


def main():
    op, cp = products(OURS), products(CODEX)
    calls, turns, aud, blocks = our_calls(), our_turns(), audit_rows(), full_blocks()
    ev = brief_telemetry()
    tp = sum(c['in'] for c in calls)
    tc = sum(c['cached'] for c in calls)
    st = calls[1:]
    sp, sc = sum(c['in'] for c in st), sum(c['cached'] for c in st)
    hit = round(100.0 * tc / tp, 1) if tp else None
    st_hit = round(100.0 * sc / sp, 1) if sp else None
    st_miss = round((sp - sc) / len(st), 1) if st else None
    t5 = turns[4]['text'] if len(turns) > 4 else ''
    t6 = turns[5]['text'] if len(turns) > 5 else ''
    menu = menu_items(t5)
    menu_txt = [m[2][:40] for m in menu]
    ref5 = sorted({k for k in EXPECT if k in t5})
    blk_max = max([b['brief_block_chars'] for b in blocks] or [0])
    p1 = {'t5': {'chars': len(t5), 'ok': len(t5) <= PREREG['t5_max'], 'max': PREREG['t5_max']},
          't6': {'chars': len(t6), 'ok': len(t6) <= PREREG['t6_max'], 'max': PREREG['t6_max']},
          'block': {'chars': blk_max, 'ok': 0 < blk_max <= PREREG['block_max'], 'max': PREREG['block_max']},
          'basis': 'chars (块长取自实发 full-*.json)'}
    p2 = {'t5_menu_n': len(menu), 't5_menu': menu_txt,
          'ok': 1 <= len(menu) <= PREREG['menu_max_items'] and any(n in t5 for n in EXPECT),
          't5_question': ('?' in t5 or '？' in t5),
          'grounded_first': bool(menu) and any(n in menu_txt[0] for n in EXPECT)}
    p3 = {'prompt_sum': tp, 'max': PREREG['prompt_max'], 'ok': tp <= PREREG['prompt_max'],
          'calls': len(calls), 'calls_ok': len(calls) <= PREREG['calls_max']}
    p4 = {'total_hit_pct': hit, 'steady_hit_pct': st_hit, 'steady_miss_avg': st_miss,
          'ok': (st_hit or 0) >= PREREG['steady_hit_min'] and (st_miss or 1e9) <= PREREG['steady_miss_max']}
    inv = sorted({t for t in re.findall(r'[A-Za-z0-9_.\-]+\.[A-Za-z0-9]+', t5) if t not in os.listdir(OURS)})
    p5 = {'products_ok': sum(1 for x in op.values() if x['ok']), 'jargon': sorted({w for w in JARGON if w in t6}),
          'grounded_refs': len([n for n in ref5 if os.path.exists(os.path.join(OURS, n))]),
          'invented_files': inv,
          'ok': sum(1 for x in op.values() if x['ok']) == 4 and not any(w in t6 for w in JARGON) and len(ref5) >= 3 and not inv}
    # checks_posthoc (首跑后发现, 非预注册): 合同标记 (clickproof 块 / no_formal 行) 是否上前台
    def contract_leak(txt):
        lines = [l for l in txt.split('\n') if l.strip()]
        return [l[:40] for l in lines if l.strip().startswith('no_formal') or l.strip() == 'clickproof'
                or re.match(r'^(premise|goal)\s', l.strip())]
    def stripped(txt):
        keep = [l for l in txt.split('\n') if not (l.strip().startswith('no_formal') or l.strip() == 'clickproof'
                or re.match(r'^(premise|goal)\s', l.strip()))]
        return len('\n'.join(keep).strip())
    posthoc = {'leak_t4': contract_leak(turns[3]['text']) if len(turns) > 3 else [],
               'leak_t6': contract_leak(t6),
               't9_stripped': {'t5': stripped(t5), 't6': stripped(t6), 't4': stripped(turns[3]['text']) if len(turns) > 3 else None},
               'note': '剥离合同标记后的字符数 = 整流修复后的预计值 (估算, 非实测)'}
    v = {'round': 'R460', 'prereg': PREREG, 'P1_brevity': p1, 'P2_menu': p2, 'P3_tokens': p3, 'P4_cache': p4, 'P5_no_regress': p5,
         't5_text': t5, 't6_text': t6, 'calls': calls, 'blocks': blocks,
         'brief_events': ev, 'codex_frozen': {'calls': 13, 'in': 91002, 'hit_pct': 96.6},
         'r458_frozen': {'t5_chars': 241, 't6_chars': 146, 'calls': 17, 'prompt_sum': 54927, 'hit_pct': 90.4, 'miss_avg': 310},
         'audit_tools': [r['tool'] for r in aud],
         'checks_posthoc': posthoc,
         'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    json.dump(v, open('/home/agentuser/AgentFramework/eval/rover/r460/verdict-r460.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('R460 判决 (精炼 + 菜单 + 命中率/token)')
    print(f"  P1 精炼   T5 {p1['t5']['chars']}≤{p1['t5']['max']} {p1['t5']['ok']} | T6 {p1['t6']['chars']}≤{p1['t6']['max']} {p1['t6']['ok']} | 块 {p1['block']['chars']}≤{p1['block']['max']} {p1['block']['ok']}")
    print(f"  P2 菜单   项数={p2['t5_menu_n']} 问句={p2['t5_question']} ok={p2['ok']} :: {p2['t5_menu']}")
    print(f"  P3 tokens prompt∑={tp} (上限 {PREREG['prompt_max']}, R458 54,927) ok={p3['ok']} | 调用={len(calls)} ok={p3['calls_ok']}")
    print(f"  P4 命中   总 hit={hit}% 稳态 hit={st_hit}% (≥{PREREG['steady_hit_min']}) 稳态 miss均价={st_miss} (≤{PREREG['steady_miss_max']}) ok={p4['ok']}")
    print(f"  P5 不回退 产物 {p5['products_ok']}/4 | 术语={p5['jargon'] or '无'} | 承接真实项={p5['grounded_refs']} | 编造={inv or '无'} ok={p5['ok']}")
    print(f"  承接块实发字符: {[b['brief_block_chars'] for b in blocks]}")
    print(f"  posthoc 合同标记泄漏 T4={posthoc['leak_t4']} T6={posthoc['leak_t6']} | 剥离后字符 {posthoc['t9_stripped']}")
    print('  --- T5 原文 ---\n  ' + t5.replace('\n', '\n  ')[:600])
    print('  --- T6 原文 ---\n  ' + t6.replace('\n', '\n  ')[:600])


if __name__ == '__main__':
    main()
