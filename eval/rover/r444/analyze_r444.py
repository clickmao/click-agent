#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R444 分析器 — 前置门(¬Ack ⇒ Pass)等价性/成本/KPI + 短档真值矩阵.

器具继承 R443 (真值口径: llama-server 上报 tokens_evaluated/prompt_new/gen_tokens),
新增:
  D4  等价性(承重): BRJ(前置门开) vs BRJL(复原) 逐轮 actual/G/J 调用/回复原文 逐位相同
  D5  成本下降: 门 r1 真值 tok(BRJL) - tok(BRJ)
  D6  KPI: 含本地真值降幅 >= 30% (M20)
  D8  矩阵: V2b/W8/W20 三档真值补列
  N1  成对正控: BRJL 必须观测到 gate:skip_rejected_nonack (否则"不可达"断言空心)
  N2  负控: BRJ 臂 skip_rejected==0 ∧ prefilter_violations==0 ∧ 门行 prefilter=1
  N3  外部真值: 桩侧调用数 == 产品自报 G/J 调用数
缺字段记 n/a 不记 0 (R418 铁律)。
"""
import json, pathlib, sys

DIR = pathlib.Path('/home/agentuser/AgentFramework/eval/rover/r444')
GRIDS = ['M20', 'V2b', 'W8']            # 本轮计划内网格 (W20 已预注册排除, 见计划 §6)
DEFERRED = ['W20']                      # 缺列 = 未测到, 禁代理
ARMS = {'M20': ['A', 'BRJ', 'BRJL'], 'V2b': ['A', 'BRJ'], 'W8': ['A', 'BRJ']}
K_N = {'M20': 7, 'V2b': 1, 'W8': 1}          # 预注册可跳轮数
LADDER = {'V2b': '0.25', 'W8': '0.125', 'M20': '0.35'}
SUF = '-s4'      # 批次 NS 后缀 (粘滞修复后的复跑用 -s5, 见 D1b)
SUF_FIX = '-s5'


def verdict(grid, arm, suf=None):
    p = DIR / f'verdict-{arm}-{grid}{suf or SUF}.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def tel(grid, arm, suf=None):
    d = DIR / f'run-{arm}-{grid}{suf or SUF}' / 'data' / 'telemetry' / 'host.jsonl'
    if not d.exists():
        return []
    out = []
    for l in d.read_text(encoding='utf-8-sig').splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    return out


def kv(r):
    return r.get('kv', r) or {}


def i_(v, d=None):
    try:
        n = int(v)
        return n if n != -1 else d
    except Exception:
        return d


def f_(v, d=None):
    try:
        return float(v)
    except Exception:
        return d


def rows_of(grid, arm, point, suf=None):
    return [kv(r) for r in tel(grid, arm, suf) if r.get('point') == point]


def d1_identity(grid, arm):
    g, j = rows_of(grid, arm, 'local_turn_gate'), rows_of(grid, arm, 'correction_judge')
    res = {'gate_rows': len(g), 'judge_rows': len(j), 'gate_checked': 0, 'judge_checked': 0,
           'gate_violations': [], 'judge_violations': [], 'gate_missing': 0, 'judge_missing': 0}
    for k in g:
        ev, nw, cn = i_(k.get('tokens_evaluated')), i_(k.get('prompt_new')), i_(k.get('cache_n'))
        if ev is None or nw is None:
            res['gate_missing'] += 1
            continue
        if cn is None:
            continue
        res['gate_checked'] += 1
        if ev != nw + cn:
            res['gate_violations'].append({'tokens_evaluated': ev, 'prompt_new': nw, 'cache_n': cn})
    for k in j:
        ev, nw, cn = i_(k.get('tokens_evaluated')), i_(k.get('prompt_new')), i_(k.get('cache_n'))
        if ev is None or nw is None:
            res['judge_missing'] += 1
            continue
        if cn is None:
            continue
        res['judge_checked'] += 1
        if ev != nw + cn:
            res['judge_violations'].append({'tokens_evaluated': ev, 'prompt_new': nw, 'cache_n': cn})
    return res


def _is_mech(k):
    return str(k.get('basis', '')).startswith('mechanical')


def gate_calls(grid, arm):
    """门 r1 调用数 (外部可检): 非机械行中带 llama-server 真值字段的门行数。"""
    return len([k for k in rows_of(grid, arm, 'local_turn_gate')
                if not _is_mech(k) and i_(k.get('tokens_evaluated')) is not None])


def sticky_rows(grid, arm, suf=None):
    """R444 器具审计: 机械判定行却携带(继承)了本地调用真值 = 粘滞字段违规。

    契约 (R443 注释) 明写「-1 = 该轮未走 r1」; 机械行既未建 prompt 也未问 r1 ⇒ 真值必须为 -1。
    旧构建 (e36d04d1 之前) 实测 M20 有 6 行粘滞 ⇒ 本地成本被虚增 2382 tok。
    """
    g = tel(grid, arm, suf)
    bad = []
    for r in g:
        if r.get('point') != 'local_turn_gate':
            continue
        k = kv(r)
        if _is_mech(k) and i_(k.get('tokens_evaluated')) is not None:
            bad.append({'basis': k.get('basis'), 'tokens_evaluated': k.get('tokens_evaluated'),
                        'gen_tokens': k.get('gen_tokens'), 'injected_tok':
                        (i_(k.get('tokens_evaluated'), 0) or 0) + (i_(k.get('gen_tokens'), 0) or 0)})
    return {'n_sticky': len(bad), 'injected_tok': sum(b['injected_tok'] for b in bad), 'rows': bad}


def local_truth(grid, arm):
    """本地 r1 成本真值 (R443 口径): 门 + 判官 的 tokens_evaluated + gen_tokens。"""
    g, j = rows_of(grid, arm, 'local_turn_gate'), rows_of(grid, arm, 'correction_judge')
    g = [k for k in g if not _is_mech(k)]          # 机械行不产生本地成本 (防粘滞虚增)
    gt = sum((i_(k.get('tokens_evaluated'), 0) or 0) + (i_(k.get('gen_tokens'), 0) or 0) for k in g)
    jt = sum((i_(k.get('tokens_evaluated'), 0) or 0) + (i_(k.get('gen_tokens'), 0) or 0) for k in j)
    g_n = len([k for k in g if i_(k.get('tokens_evaluated')) is not None])
    j_n = len([k for k in j if i_(k.get('tokens_evaluated')) is not None])
    return {'gate': gt, 'judge': jt, 'total': gt + jt, 'gate_truth_rows': g_n, 'judge_truth_rows': j_n}


def local_est(grid, arm):
    """「字符/2」折算 (对照口径, R443 已证低估)."""
    g, j = rows_of(grid, arm, 'local_turn_gate'), rows_of(grid, arm, 'correction_judge')
    g = [k for k in g if not _is_mech(k)]
    gt = sum(((i_(k.get('gate_prompt_len'), 0) or 0) + (i_(k.get('raw_len'), 0) or 0)) / 2.0 for k in g)
    jt = sum((i_(k.get('prompt_len'), 0) or 0) / 2.0 for k in j)
    return {'gate': gt, 'judge': jt, 'total': gt + jt}


def d2_truth_ratio(grid, arm):
    g, j = rows_of(grid, arm, 'local_turn_gate'), rows_of(grid, arm, 'correction_judge')
    g = [k for k in g if not _is_mech(k)]
    gp = sum(i_(k.get('tokens_evaluated'), 0) or 0 for k in g)
    gc = sum((i_(k.get('gate_prompt_len'), 0) or 0) / 2.0 for k in g)
    gg = sum(i_(k.get('gen_tokens'), 0) or 0 for k in g)
    gch = sum((i_(k.get('raw_len'), 0) or 0) / 2.0 for k in g)
    jp = sum(i_(k.get('tokens_evaluated'), 0) or 0 for k in j)
    jc = sum((i_(k.get('prompt_len'), 0) or 0) / 2.0 for k in j)
    return {'gate_prompt_true': gp, 'gate_prompt_est': round(gc, 1), 'gate_prompt_ratio': round(gp / gc, 3) if gc else None,
            'gate_gen_true': gg, 'gate_gen_est': round(gch, 1), 'gate_gen_ratio': round(gg / gch, 3) if gch else None,
            'judge_prompt_true': jp, 'judge_prompt_est': round(jc, 1), 'judge_prompt_ratio': round(jp / jc, 3) if jc else None}


def d3_drops(grid):
    a, b = verdict(grid, 'A'), verdict(grid, 'BRJ')
    if not a or not b:
        return None
    A = a['tokens_total']
    lt, le = local_truth(grid, 'BRJ'), local_est(grid, 'BRJ')
    return {'A_remote': A, 'BRJ_remote': b['tokens_total'],
            'D_remote': round(100 * (1 - b['tokens_total'] / A), 2),
            'D_remote_plus_local_true': round(100 * (1 - (b['tokens_total'] + lt['total']) / A), 2),
            'D_remote_plus_local_est': round(100 * (1 - (b['tokens_total'] + le['total']) / A), 2),
            'D_remote_minus_local_true': round(100 * (1 - (b['tokens_total'] - lt['total']) / A), 2),
            'local_true': lt, 'local_est': le, 'k_over_N': f"{K_N[grid]}/{len(b['per_turn'])}"}


def _cmp_turns(pb, pl):
    """逐轮逐位比较 (纯函数, 供 d4 与自身负控共用)。"""
    diffs = []
    for t in sorted(set(pb) | set(pl)):
        x, y = pb.get(t, {}), pl.get(t, {})
        for f in ('actual', 'G_calls', 'J_calls', 'reply_source', 'reply_len'):
            if x.get(f) != y.get(f):
                diffs.append({'turn': t, 'field': f, 'BRJ': x.get(f), 'BRJL': y.get(f)})
        if x.get('reply_head') != y.get('reply_head'):
            diffs.append({'turn': t, 'field': 'reply_head', 'BRJ': x.get('reply_head'), 'BRJL': y.get('reply_head')})
    return diffs


def d4_equivalence(neg_control=False):
    """承重: BRJ(前置门开) vs BRJL(复原) — 逐轮逐位等价。"""
    b, l = verdict('M20', 'BRJ'), verdict('M20', 'BRJL')
    if not b or not l:
        return None
    pb = {t['turn']: dict(t) for t in b['per_turn']}
    pl = {t['turn']: dict(t) for t in l['per_turn']}
    if neg_control and pb:
        k = sorted(pb)[0]
        pb[k]['actual'] = '__neg_control__'
        diffs = _cmp_turns(pb, pl)
        detected = len(diffs) >= 1
        print(f"负控注入: 期望检出 >=1 差异 ⇒ {'OK(检出)' if detected else 'HOLLOW(未检出 ⇒ 比较器空心)'}; 检出 {len(diffs)} 条")
        return {'neg_control': True, 'detected': int(len(diffs)), 'per_turn_diffs': diffs}
    diffs = _cmp_turns(pb, pl)
    gb, gl = rows_of('M20', 'BRJ', 'local_turn_gate'), rows_of('M20', 'BRJL', 'local_turn_gate')
    basis_b = [str(k.get('basis', '')) for k in gb]
    basis_l = [str(k.get('basis', '')) for k in gl]
    return {'per_turn_diffs': diffs, 'per_turn_identical': not diffs,
            'remote_tokens_identical': b['tokens_total'] == l['tokens_total'],
            'G_tokens_BRJ': b['G_tokens'], 'G_tokens_BRJL': l['G_tokens'],
            'J_tokens_BRJ': b['J_tokens'], 'J_tokens_BRJL': l['J_tokens'],
            'gate_r1_calls_BRJ': gate_calls('M20', 'BRJ'), 'gate_r1_calls_BRJL': gate_calls('M20', 'BRJL'),
            'gate_rows_BRJ': len(gb), 'gate_rows_BRJL': len(gl),
            'basis_BRJ': sorted(set(basis_b)), 'basis_BRJL': sorted(set(basis_l)),
            'prefilter_flag_BRJ': sorted({str(k.get('prefilter', '')) for k in gb}),
            'prefilter_flag_BRJL': sorted({str(k.get('prefilter', '')) for k in gl})}


def d5_cost():
    b, l = local_truth('M20', 'BRJ'), local_truth('M20', 'BRJL')
    if not verdict('M20', 'BRJ') or not verdict('M20', 'BRJL'):
        return None
    saved = l['total'] - b['total']
    calls = gate_calls('M20', 'BRJL') - gate_calls('M20', 'BRJ')
    return {'local_true_BRJ': b, 'local_true_BRJL': l, 'saved_tok': saved, 'saved_calls': calls,
            'gate_calls_BRJ': gate_calls('M20', 'BRJ'), 'gate_calls_BRJL': gate_calls('M20', 'BRJL'),
            'judge_calls_BRJ': len(rows_of('M20', 'BRJ', 'correction_judge')),
            'judge_calls_BRJL': len(rows_of('M20', 'BRJL', 'correction_judge')),
            'per_call_saved': round(saved / calls, 1) if calls else None}


def d7_quality(grid, arm):
    v = verdict(grid, arm)
    if not v:
        return None
    return {'fn_n': v['fn_n'], 'fp_n': v['fp_n'], 'accuracy': v['accuracy'],
            'measured_turns': v['measured_n'], 'consumed_as_ask': v['consumed_as_ask_answer']}


def d1b_sticky_verdict():
    """R444 粘滞字段缺陷: 成对判据 (旧构建必有 ∧ 修复版必 0 ∧ 行为零差)。"""
    o = sticky_rows('M20', 'BRJ', SUF)
    f = sticky_rows('M20', 'BRJ', SUF_FIX)
    v4, v5 = verdict('M20', 'BRJ', SUF), verdict('M20', 'BRJ', SUF_FIX)
    res = {'old_n_sticky': o['n_sticky'], 'old_injected_tok': o['injected_tok'],
           'fixed_n_sticky': f['n_sticky'], 'fixed_injected_tok': f['injected_tok'],
           'BRJ_local_truth_with_sticky': None, 'BRJ_local_truth_honest': None}
    if v4 and v5:
        pb = {t['turn']: t for t in v4['per_turn']}
        pl = {t['turn']: t for t in v5['per_turn']}
        res['per_turn_diffs'] = len(_cmp_turns(pb, pl))
        res['remote_tokens_equal'] = v4['tokens_total'] == v5['tokens_total']
        res['remote_tokens'] = {'s4': v4['tokens_total'], 's5': v5['tokens_total']}
        res['pass'] = bool(o['n_sticky'] > 0 and f['n_sticky'] == 0 and res['per_turn_diffs'] == 0
                           and res['remote_tokens_equal'])
    else:
        res['pass'] = False
        res['note'] = '未测到 (缺 -s5 复跑臂)'
    return res


def n1_positive_control():
    gl = rows_of('M20', 'BRJL', 'local_turn_gate')
    gb = rows_of('M20', 'BRJ', 'local_turn_gate')
    rej_l = [k for k in gl if str(k.get('basis', '')).startswith('gate:skip_rejected_nonack')]
    rej_b = [k for k in gb if str(k.get('basis', '')).startswith('gate:skip_rejected_nonack')]
    fl_l = sorted({str(k.get('prefilter', '')) for k in gl})
    fl_b = sorted({str(k.get('prefilter', '')) for k in gb})
    viol_b = max([i_(k.get('prefilter_violations'), 0) or 0 for k in gb] or [0])
    nonack_b = [k for k in gb if str(k.get('basis', '')).startswith('mechanical:nonack')]
    nonack_l = [k for k in gl if str(k.get('basis', '')).startswith('mechanical:nonack')]
    return {'BRJL_skip_rejected_n': len(rej_l), 'BRJ_skip_rejected_n': len(rej_b),
            'BRJL_prefilter_flag': fl_l, 'BRJ_prefilter_flag': fl_b,
            'BRJ_violations': viol_b, 'BRJ_nonack_rows': len(nonack_b), 'BRJL_nonack_rows': len(nonack_l),
            'PASS_N1_正控': len(rej_l) >= 3 and fl_l == ['0'],
            'PASS_N2_负控': len(rej_b) == 0 and viol_b == 0 and fl_b == ['1']}


def n3_external_truth(grid, arm):
    v = verdict(grid, arm)
    if not v:
        return None
    return {'stub_calls': v['calls_total'], 'G_calls': v['G_calls'], 'J_calls': v['J_calls'],
            'unassigned': v['unassigned_calls'], 'attribution_ok': v['attribution_ok']}


def main():
    neg = '--neg-control' in sys.argv
    if neg:
        d4x = d4_equivalence(neg_control=True)
        return 0 if d4x and d4x['detected'] >= 1 else 9
    res = {'round': 'R444', 'dir': str(DIR)}
    res['D1'] = {f'{g}/{a}': d1_identity(g, a) for g in GRIDS for a in ARMS[g]}
    res['D2'] = {f'{g}/{a}': d2_truth_ratio(g, a) for g in GRIDS for a in ARMS[g] if a != 'A'}
    res['D3'] = {g: d3_drops(g) for g in GRIDS}
    res['D4_equivalence'] = d4_equivalence()
    res['D5_cost'] = d5_cost()
    res['D7_quality'] = {f'{g}/{a}': d7_quality(g, a) for g in GRIDS for a in ARMS[g]}
    res['D1b_sticky'] = {'old_build_s4': {'M20/BRJ': sticky_rows('M20', 'BRJ'), 'M20/BRJL': sticky_rows('M20', 'BRJL')},
                         'fixed_build_s5': {'M20/BRJ': sticky_rows('M20', 'BRJ', SUF_FIX)},
                         'verdict': d1b_sticky_verdict()}
    res['N1N2'] = n1_positive_control()
    res['N3'] = {f'{g}/{a}': n3_external_truth(g, a) for g in GRIDS for a in ARMS[g]}

    print('=== D1 记账恒等 (tokens_evaluated == prompt_new + cache_n) ===')
    for k, v in res['D1'].items():
        print(f"  {k:10s} 门{v['gate_rows']:3d}行(核{v['gate_checked']:3d}) 违规{len(v['gate_violations'])} "
              f"| 判官{v['judge_rows']:3d}行(核{v['judge_checked']:3d}) 违规{len(v['judge_violations'])} 缺{v['judge_missing']}")
    print('=== D2 真值 vs 字符/2 ===')
    for k, v in res['D2'].items():
        print(f"  {k:10s} 门prompt {v['gate_prompt_true']} vs {v['gate_prompt_est']} = {v['gate_prompt_ratio']}x "
              f"| 门gen {v['gate_gen_true']} vs {v['gate_gen_est']} = {v['gate_gen_ratio']}x "
              f"| 判官prompt {v['judge_prompt_true']} vs {v['judge_prompt_est']} = {v['judge_prompt_ratio']}x")
    print('=== D3 口径三档 ===')
    for g, v in res['D3'].items():
        if not v:
            print(f'  {g}: 缺臂'); continue
        print(f"  {g:4s} k/N={v['k_over_N']:6s} A={v['A_remote']:6d} BRJ={v['BRJ_remote']:6d} "
              f"| 远端 {v['D_remote']:6.2f}% | +本地真值 {v['D_remote_plus_local_true']:6.2f}% "
              f"| +本地折算 {v['D_remote_plus_local_est']:6.2f}% | 减本地 {v['D_remote_minus_local_true']:6.2f}%")
    print('=== D4 等价性 (BRJ vs BRJL, 承重) ===')
    d4 = res['D4_equivalence']
    if d4:
        print(f"  逐轮差异 {len(d4['per_turn_diffs'])} 条 | 远端tok相同={d4['remote_tokens_identical']} "
              f"| 门r1调用 BRJ={d4['gate_r1_calls_BRJ']} vs BRJL={d4['gate_r1_calls_BRJL']}")
        print(f"  G_tokens {d4['G_tokens_BRJ']} vs {d4['G_tokens_BRJL']} | J_tokens {d4['J_tokens_BRJ']} vs {d4['J_tokens_BRJL']}")
        print(f"  basis BRJ={d4['basis_BRJ']}")
        print(f"  basis BRJL={d4['basis_BRJL']}")
        print(f"  prefilter flag BRJ={d4['prefilter_flag_BRJ']} BRJL={d4['prefilter_flag_BRJL']}")
        for d in d4['per_turn_diffs'][:6]:
            print('   差异:', d)
    print('=== D5 成本下降 ===')
    if res['D5_cost']:
        c = res['D5_cost']
        print(f"  本地真值tok BRJ={c['local_true_BRJ']['total']} (门{c['local_true_BRJ']['gate']}/判官{c['local_true_BRJ']['judge']}) "
              f"vs BRJL={c['local_true_BRJL']['total']} (门{c['local_true_BRJL']['gate']}/判官{c['local_true_BRJL']['judge']})")
        print(f"  省 {c['saved_tok']} tok / {c['saved_calls']} 次调用 = {c['per_call_saved']} tok/调用")
    print('=== D1b 粘滞字段成对判据 (旧构建必有 ∧ 修复版必 0 ∧ 行为零差) ===')
    print(' ', json.dumps(res['D1b_sticky']['verdict'], ensure_ascii=False))
    print('=== N1/N2 成对判据 ===')
    print(' ', json.dumps(res['N1N2'], ensure_ascii=False))
    print('=== D7 质量 ===')
    for k, v in res['D7_quality'].items():
        if v:
            print(f"  {k:10s} fn={v['fn_n']} fp={v['fp_n']} acc={v['accuracy']} 实测轮={v['measured_turns']} 吞并={v['consumed_as_ask']}")
    print('=== N3 外部真值 (桩侧==自报) ===')
    for k, v in res['N3'].items():
        if v:
            print(f"  {k:10s} 桩{v['stub_calls']:3d} = G{v['G_calls']:3d}+J{v['J_calls']:3d}+未归属{v['unassigned']} ok={v['attribution_ok']}")
    missing = [f'{g}/{a}' for g in GRIDS for a in ARMS[g] if not verdict(g, a)]
    if missing:
        print('缺臂(fail-closed, 禁跨网格代理):', missing)
        return 1
    (DIR / 'verdict-r444-analysis.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print('已落盘:', DIR / 'verdict-r444-analysis.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
