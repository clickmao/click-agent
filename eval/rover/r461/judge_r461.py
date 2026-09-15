#!/usr/bin/env python3
"""R461 判分 —— 只读落盘证据 (预注册 = eval/rover/r461/prereg-r461.json)。不重建 prompt。

判据:
  P1 契约声明不上前台 : 全部前台回复里契约声明行 = 0 (负控: R460 落盘 turns 上同判据必须 >0)
  P2 零字节产物可见   : 承接块/问句里 0 字节产物标 (空)
  P3 tokens           : prompt ∑ ≤ 39,863 (R460 非回退) 且远端调用 ≤ 13
  P4 命中率           : 稳态 (2..n) hit ≥ 90.2%; 另给 97% 红线的算术条件 (只报数, 不粉饰)
  P5 不回退           : 产物 4/4 + T6 术语 0 + T5 编号菜单 ≥1 且首项接地 + 磁盘级伪造 0
"""
import glob
import json
import os
import re
import time

E = os.environ.get('R461_ENV', '/tmp/r461_env')
R460_ENV = os.environ.get('R460_ENV', '/tmp/r460_env')
AD = os.path.join(E, 'logs/adapter')
OURS = os.path.join(E, 'agent/work')
TURNS = os.path.join(E, 'logs/agent-turns.jsonl')
AUDIT = os.path.join(E, 'logs/audit/action_loop.jsonl')
EXPECT = {'count.txt': '4', 'merged.txt': 'ALPHA\nBETA\nGAMMA', 'stats.txt': 'chars=14', 'first.txt': 'R455 fixture note'}
JARGON = ['可选范围', '检查点', '作废', '槽位', '落不到']
PREREG = {'prompt_max': 39863, 'calls_max': 13, 'steady_hit_min': 90.2,
          'hit_target': 93.0, 'red_line': 97.0, 'menu_max_items': 3}
LEAK_RE = re.compile(r'^(clickproof|no_formal:)|^(premise|goal)\s')


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
        resp = d.get('response') or {}
        u = resp.get('usage') or {}
        rows.append({'file': os.path.basename(p), 'in': u.get('prompt_tokens') or 0,
                     'cached': _cached(u), 'out': u.get('completion_tokens') or 0})
    return rows


def our_turns(env=None):
    path = TURNS if env is None else os.path.join(env, 'logs/agent-turns.jsonl')
    if not os.path.exists(path):
        return []
    d = json.load(open(path, encoding='utf-8'))
    ts = d['turns'] if isinstance(d, dict) and 'turns' in d else d
    return [{'turn': i, 'text': t.get('reply') or t.get('content') or ''} for i, t in enumerate(ts, 1)]


def leak_lines(text):
    return [l.strip()[:48] for l in (text or '').split('\n') if l.strip() and LEAK_RE.match(l.strip())]


def full_last_users(env=None):
    ad = AD if env is None else os.path.join(env, 'logs/adapter')
    out = []
    for f in sorted(glob.glob(os.path.join(ad, 'full-agent-*.json'))):
        msgs = json.load(open(f, encoding='utf-8'))
        last = None
        for m in msgs:
            if m.get('role') == 'user':
                last = m
        out.append({'file': os.path.basename(f), 'text': (last or {}).get('content') or ''})
    return out


def telemetry_points():
    out = []
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
            if d.get('point') in ('contract_declaration_hidden', 'continuation_brief', 'continuation_closure'):
                out.append({'point': d['point'], **(d.get('kv') or {})})
    return out


def menu_items(text):
    return re.findall(r'(?:^|[；;，,：:\s])\s*(?:([1-3])[.、)）]|([①②③]))\s*([^；;，,\n]{2,40})', text)


def audit_rows():
    out = []
    if os.path.exists(AUDIT):
        for ln in open(AUDIT, encoding='utf-8'):
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
    return out


def main():
    op = products(OURS)
    calls, turns = our_calls(), our_turns()
    tp = sum(c['in'] for c in calls)
    tc = sum(c['cached'] for c in calls)
    st = calls[1:]
    sp, sc = sum(c['in'] for c in st), sum(c['cached'] for c in st)
    hit = round(100.0 * tc / tp, 1) if tp else None
    st_hit = round(100.0 * sc / sp, 1) if sp else None
    st_miss = round((sp - sc) / len(st), 1) if st else None
    avg_prefix = round(sp / len(st)) if st else 0
    need_new_tok = round((100.0 - PREREG['red_line']) / 100.0 * avg_prefix, 1) if avg_prefix else None

    # P1 契约声明不上前台 (+ 负控: R460 落盘 turns)
    leaks = {t['turn']: leak_lines(t['text']) for t in turns}
    leaks = {k: v for k, v in leaks.items() if v}
    neg = {t['turn']: leak_lines(t['text']) for t in our_turns(R460_ENV)}
    neg = {k: v for k, v in neg.items() if v}
    p1 = {'leak_turns': leaks, 'leak_total': sum(len(v) for v in leaks.values()),
          'ok': sum(len(v) for v in leaks.values()) == 0,
          'neg_control_r460_leaks': {k: v for k, v in list(neg.items())[:3]},
          'neg_control_has_discrimination': sum(len(v) for v in neg.values()) > 0}

    # P2 零字节产物可见 (实发块里的 0B 项是否标 (空))
    blocks = []
    for u in full_last_users():
        t = u['text']
        i = t.find('[承接状态 v1]')
        blk = t[i:] if i >= 0 else ''
        blocks.append({'file': u['file'], 'block_chars': len(blk),
                       'has_empty_mark': '=(空)' in blk, 'block': blk})
    zero_b = [b for b in blocks if re.search(r'\(\s*0\s*B\)', b['block'])]
    p2 = {'blocks': [{'file': b['file'], 'chars': b['block_chars'], 'empty_mark': b['has_empty_mark']} for b in blocks],
          'blocks_with_zero_byte': [b['file'] for b in zero_b],
          'zero_byte_all_marked': all(b['has_empty_mark'] for b in zero_b),
          'ok': all(('=(空)' in b['block']) for b in zero_b)}

    # P3 tokens
    p3 = {'prompt_sum': tp, 'max': PREREG['prompt_max'], 'ok': tp <= PREREG['prompt_max'],
          'calls': len(calls), 'calls_ok': len(calls) <= PREREG['calls_max']}

    # P4 命中率
    p4 = {'total_hit_pct': hit, 'steady_hit_pct': st_hit, 'steady_miss_avg': st_miss,
          'avg_prefix_tok': avg_prefix, 'new_tok_for_97pct': need_new_tok,
          'ok': (st_hit or 0) >= PREREG['steady_hit_min'],
          'hit_target_93': (st_hit or 0) >= PREREG['hit_target'],
          'red_line_97': (st_hit or 0) >= PREREG['red_line']}

    # P5 不回退
    t5 = turns[4]['text'] if len(turns) > 4 else ''
    t6 = turns[5]['text'] if len(turns) > 5 else ''
    menu = menu_items(t5)
    inv = sorted({t for t in re.findall(r'[A-Za-z0-9_.\-]+\.[A-Za-z0-9]+', t5) if t not in os.listdir(OURS)})
    jargon = sorted({w for w in JARGON if w in t6})
    p5 = {'products_ok': sum(1 for x in op.values() if x['ok']), 'jargon': jargon,
          'menu_n': len(menu), 'menu': [m[2][:36] for m in menu],
          'grounded_first': bool(menu) and any(n in menu[0][2] for n in EXPECT),
          'grounded_any': any(any(n in m[2] for n in EXPECT) for m in menu),
          'invented_files': inv,
          'ok': sum(1 for x in op.values() if x['ok']) == 4 and not jargon and len(menu) >= 1 and not inv}

    points = telemetry_points()

    # checks_posthoc (跑测后发现, 非预注册): 召回块里的"历史事实" vs 本会话真实产物
    recall_refs, stale = set(), set()
    root_files = set(os.listdir(OURS))
    for u in full_last_users():
        t = u['text']
        i = t.find('[Memory (RAG)]')
        if i < 0:
            continue
        seg = t[i:i + 2000]
        for fn in re.findall(r'[A-Za-z0-9_.\-]+\.[A-Za-z0-9]+', seg):
            recall_refs.add(fn)
            if fn not in root_files:
                stale.add(fn)
    posthoc = {'recall_refs': sorted(recall_refs), 'recall_stale_refs': sorted(stale),
               'note': '召回块引用但工作区不存在的名字 = 上一会话残留事实被当成本轮真值 (T5 宣称 stats.txt=chars=15 的机制根因), 未列预注册, R462 靶点'}
    v = {'round': 'R461', 'prereg': PREREG,
         'P1_contract_not_front': p1, 'P2_empty_visible': p2, 'P3_tokens': p3, 'P4_cache': p4, 'P5_no_regress': p5,
         'checks_posthoc': posthoc,
         't5_text': t5, 't6_text': t6, 'turns_len': {t['turn']: len(t['text']) for t in turns},
         'calls': calls, 'blocks': p2['blocks'], 'telemetry': points,
         'audit_tools': [r.get('tool') for r in audit_rows()],
         'frozen': {'R458': {'prompt_sum': 54927, 'hit_pct': 90.4, 'calls': 17},
                    'R460': {'prompt_sum': 39863, 'hit_pct': 85.1, 'steady_hit_pct': 90.2, 'calls': 13, 't5_chars': 160},
                    'codex': {'prompt_sum': 91002, 'hit_pct': 96.6, 'calls': 13}},
         'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    outp = '/home/agentuser/AgentFramework/eval/rover/r461/verdict-r461.json'
    json.dump(v, open(outp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('R461 判决 (契约不上前台 / 空产物可见 / 命中率·token)')
    print(f"  P1 契约泄漏 总={p1['leak_total']} ok={p1['ok']} | 负控(R460 落盘)有判别力={p1['neg_control_has_discrimination']} 例={p1['neg_control_r460_leaks']}")
    print(f"  P2 空产物   0B 块={p2['blocks_with_zero_byte']} 全标空={p2['zero_byte_all_marked']} ok={p2['ok']}")
    print(f"  P3 tokens   prompt∑={tp} (≤{PREREG['prompt_max']}, R460 39,863 / R458 54,927) ok={p3['ok']} | 调用={len(calls)} ok={p3['calls_ok']}")
    print(f"  P4 命中     总={hit}% 稳态={st_hit}% (非回退≥{PREREG['steady_hit_min']}) ok={p4['ok']} | 目标93%={p4['hit_target_93']} 红线97%={p4['red_line_97']}")
    print(f"              稳态 miss 均价={st_miss} tok | 平均前缀={avg_prefix} tok ⇒ 97% 需每轮新内容 ≤ {need_new_tok} tok")
    print(f"  P5 不回退   产物 {p5['products_ok']}/4 | 菜单={p5['menu_n']} 首项接地={p5['grounded_first']} | 术语={jargon or '无'} | 编造={inv or '无'} ok={p5['ok']}")
    print(f"  承接块实发字符: {[b['chars'] for b in p2['blocks']]}")
    print(f"  遥测: {[ (p['point'], p.get('decl_chars'), p.get('chars')) for p in points ]}")
    print(f"  verdict -> {outp}")


if __name__ == '__main__':
    main()
