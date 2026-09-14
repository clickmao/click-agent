#!/usr/bin/env python3
"""R440 机判器 — 预注册判据 C1..C7（**只实现** docs/plans/v0.60.0-r440-length-ladder-measurement.md §3 的写法）
+ 事后校核 H1..H3（单列, 不得与预注册混算; 预注册判据被证伪时按纪律「宣称收窄 + 事后单列」）。

用法: python3 compare_r440.py   （读同目录 verdict-*.json + predict-r440*-pre.json ⇒ 写 compare-r440.json）
"""
import json
import pathlib

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
D = ROOT / 'eval/rover/r440'
D439 = ROOT / 'eval/rover/r439'
L = lambda p: json.load(open(p, encoding='utf-8'))
PREREG = L(D / 'predict-r440-pre.json')
PREREG_B = L(D / 'predict-r440b-pre.json')
GRIDS = ['V1', 'V2', 'V2b', 'V4', 'V5']
PREREG_MODEL_POS_DELTA_PT = -1.2   # 计划 §3 C7 逐字: 「模型预测 ≈ −1.2 pt」


def arm(g, a):
    for suffix in ('', '-b1'):
        f = D / f'verdict-{a}-{g}{suffix}.json'
        if f.exists():
            return L(f)
    return None


def row(g, a):
    v = arm(g, a)
    if not v:
        return None
    pt = v['per_turn']
    return {'tokens': v['tokens_total'], 'calls': v['calls_total'],
            'consumed': sorted(r['turn'] for r in pt if r.get('consumed_as_ask_answer')),
            'skips': sorted(r['turn'] for r in pt if r.get('actual') == 'skip'),
            'fn': v['fn_n'], 'fp': v['fp_n'], 'acc': round(v['accuracy'], 4),
            'unassigned': v.get('unassigned_calls'), 'jrem': v.get('judge_remote_fallback_n'),
            'persist': {r['turn']: r for r in pt}}


T = {g: {a: row(g, a) for a in ('A', 'BRJ', 'BP')} for g in GRIDS}
V20 = {'A': L(D439 / 'verdict-A-V20.json'), 'BRJ': L(D439 / 'verdict-BRJ-V20.json')}
V20_T = {k: v['tokens_total'] for k, v in V20.items()}
P8A = L(ROOT / 'eval/rover/r436/verdict-A-p8.json')
P12A = L(ROOT / 'eval/rover/r436/verdict-A-p12.json')


def pt_map(v):
    return {r['turn']: (r.get('G_tokens') or 0) for r in v['per_turn']}


def drop(g, a='BRJ'):
    t = T[g]
    return None if not (t['A'] and t[a]) else 100 * (1 - t[a]['tokens'] / t['A']['tokens'])


def delta_emp(g):
    """δ = B(i) − A(i), 只取两臂均为**单调用**且非跳的轮（多调用轮无逐轮可比口径）。"""
    t = T[g]
    pa, pb = t['A']['persist'], t['BRJ']['persist']
    ds = [pb[k]['G_tokens'] - pa[k]['G_tokens'] for k in sorted(pb)
          if pb[k].get('actual') == 'pass' and pa.get(k, {}).get('G_calls') == 1 and pb[k].get('G_calls') == 1]
    return (sum(ds) / len(ds) if ds else None), len(ds)


def reanchored(g):
    """H2 事后: δ 取同网格实测常数, A 分母取同网格 A 臂全部携带调用的轮实测 G_tokens。"""
    t = T[g]
    pa, pb = t['A']['persist'], t['BRJ']['persist']
    d, _ = delta_emp(g)
    calls = [k for k in sorted(pb) if pb[k].get('actual') == 'pass']
    a_all = sum(pa[k]['G_tokens'] for k in sorted(pa) if (pa[k].get('G_tokens') or 0) > 0)
    b_pred = sum(pa[k]['G_tokens'] for k in calls) + d * len(calls)
    return {'A_denom_tok': a_all, 'B_pred_tok': round(b_pred, 1), 'pred_drop_pct': round(100 * (1 - b_pred / a_all), 4),
            'measured_drop_pct': round(drop(g), 4), 'dev_pt': round(100 * (1 - b_pred / a_all) - drop(g), 4)}


checks = {}
checks['C1_door_quality'] = {g: {'fn': T[g]['BRJ']['fn'], 'fp': T[g]['BRJ']['fp'], 'acc': T[g]['BRJ']['acc']} for g in GRIDS}
checks['C1_door_quality']['pass'] = all(T[g]['BRJ']['fn'] == 0 and T[g]['BRJ']['fp'] == 0 and T[g]['BRJ']['acc'] == 1.0 for g in GRIDS)

# C2 分母复现（逐字预注册: V1/V2 与 p8 同位置逐位同值; V4/V5 与 V20 同长同文本逐位同值）
def per_turn_cmp(gA, gB):
    ma, mb = pt_map(gA), pt_map(gB)
    common = [k for k in sorted(set(ma) & set(mb)) if ma[k] and mb[k]]
    eq = [k for k in common if ma[k] == mb[k]]
    worst = max(((abs(ma[k] - mb[k]), k, ma[k], mb[k]) for k in common), default=None)
    return {'turns_compared': len(common), 'turns_bit_equal': len(eq), 'worst': worst,
            'total_delta_pct': round(100 * (gA['tokens_total'] / gB['tokens_total'] - 1), 4)}
c2 = {'V1_vs_p8A': per_turn_cmp(L(D / 'verdict-A-V1.json'), P8A),
      'V4_vs_V20A': per_turn_cmp(L(D / 'verdict-A-V4.json'), V20['A']),
      'V5_vs_V20A': per_turn_cmp(L(D / 'verdict-A-V5.json'), V20['A'])}
c2['strict_pass'] = (c2['V1_vs_p8A']['turns_bit_equal'] == c2['V1_vs_p8A']['turns_compared'] and
                     c2['V4_vs_V20A']['turns_bit_equal'] == c2['V4_vs_V20A']['turns_compared'] and
                     c2['V5_vs_V20A']['turns_bit_equal'] == c2['V5_vs_V20A']['turns_compared'])
c2['total_level_pass'] = all(abs(c2[k]['total_delta_pct']) <= 2.0 for k in ('V1_vs_p8A', 'V4_vs_V20A', 'V5_vs_V20A'))
c2['pass'] = c2['strict_pass']
checks['C2_A_denominator'] = c2
# C2b 事后: 预注册的「逐位同值」被证伪 ⇒ 单列「总量级(≤2%)」是否成立
checks['C2b_total_level_posthoc'] = {'pass': c2['total_level_pass'],
                                     'note': '预注册的逐位形式被证伪(同长同文本 ≠ 历史同构 ⇒ 逐轮 prompt 差最大见 worst); 总量级 ≤2% 是事后收窄口径'}

c3 = {}
for g in GRIDS:
    if g == 'V2b':
        real = (tuple(T['V2b']['BRJ']['skips']), tuple(T['V2b']['BRJ']['consumed']))
        name = {'((4,), (2,))': 'B2a_t2_eaten', '((2,), (4,))': 'B2b_t4_eaten', '((2, 4), ())': 'B1_no_consumption',
                '((), (2, 4))': 'B3_both_acks_eaten', '((2, 4), (3,))': 'B4_real_t3_eaten'}.get(str(real))
        p = PREREG_B['branches'].get(name) if name else None
        c3[g] = {'realized_skips': real[0], 'realized_consumed': real[1], 'branch': name,
                 'pred': (p or {}).get('pred_drop_pct'), 'measured': round(drop(g), 4),
                 'dev_pt': round(drop(g) - p['pred_drop_pct'], 4) if p else None,
                 'pass': bool(p) and abs(drop(g) - p['pred_drop_pct']) <= 3.0}
    else:
        p = PREREG['predictions'][g]
        c3[g] = {'pred': p['pred_drop_pct'], 'measured': round(drop(g), 4), 'dev_pt': round(drop(g) - p['pred_drop_pct'], 4),
                 'A_source': p['A_source'], 'pass': abs(drop(g) - p['pred_drop_pct']) <= 3.0}
checks['C3_prediction_within_3pt'] = c3
checks['C4_zero_skip_negative'] = {'V1': round(drop('V1'), 4), 'V5': round(drop('V5'), 4),
                                   'pass': drop('V1') < 0 and drop('V5') < 0}
checks['C5_bp_negative_control'] = {'BP_drop': round(drop('V4', 'BP'), 4), 'BP_jrem': T['V4']['BP']['jrem'],
                                    'BP_skips': T['V4']['BP']['skips'],
                                    'pass': drop('V4', 'BP') <= 0 and (T['V4']['BP']['jrem'] or 0) > 0}
checks['C6_quality_no_regression'] = {'pass': all(T[g]['BRJ']['acc'] == 1.0 and T[g]['BRJ']['unassigned'] == 0 for g in GRIDS),
                                      'unassigned': {g: T[g]['BRJ']['unassigned'] for g in GRIDS},
                                      'fn': {g: T[g]['BRJ']['fn'] for g in GRIDS}, 'fp': {g: T[g]['BRJ']['fp'] for g in GRIDS}}
d_v4 = drop('V4')
d_v20 = 100 * (1 - V20_T['BRJ'] / V20_T['A'])
checks['C7_position_single_variable'] = {'measured_delta_pt': round(d_v4 - d_v20, 4), 'prereg_model_delta_pt': PREREG_MODEL_POS_DELTA_PT,
                                         'dev_pt': round((d_v4 - d_v20) - PREREG_MODEL_POS_DELTA_PT, 4),
                                         'pass': abs((d_v4 - d_v20) - PREREG_MODEL_POS_DELTA_PT) <= 3.0}

checks['H1_delta_law_posthoc'] = {g: {'delta_emp_tok': delta_emp(g)[0], 'n_single_call_turns': delta_emp(g)[1]} for g in GRIDS}
checks['H2_reanchored_model_posthoc'] = {g: reanchored(g) for g in GRIDS}
checks['H2_reanchored_model_posthoc']['all_within_1pt'] = all(abs(v['dev_pt']) <= 1.0 for k, v in checks['H2_reanchored_model_posthoc'].items() if isinstance(v, dict))
checks['H3_prereg_defects_posthoc'] = {
    'A_proxy_inflation_pct': {g: round(100 * (PREREG['predictions'][g]['A_total'] / T[g]['A']['tokens'] - 1), 4) for g in ('V4', 'V5')},
    'prereg_A_total': {g: PREREG['predictions'][g]['A_total'] for g in ('V4', 'V5')},
    'measured_A_total': {g: T[g]['A']['tokens'] for g in ('V4', 'V5')},
    'delta_law': {'prereg_delta_at_t14_20': [round(PREREG['model']['delta_role_offset']['d0'] + PREREG['model']['delta_role_offset']['d1'] * t, 1) for t in (14, 17, 20)],
                  'measured_delta_const': checks['H1_delta_law_posthoc']['V4']['delta_emp_tok']},
    'root_cause': '① A 分母跨网格「逐记录下标」代理 ⇒ 多调用轮导致位移(V20 A 臂 25 调用/20 轮); ② δ(i) 线性外推来自 p12 拟合, 实测为常数。二者共同抬高预注册 B 与 A。'}

out = {'round': 'R440', 'ts_utc_plus8': None, 'preregistered_checks': checks,
       'table': {g: {a: (None if not T[g][a] else {k: T[g][a][k] for k in ('tokens', 'calls', 'consumed', 'skips', 'fn', 'fp', 'acc')}) for a in ('A', 'BRJ', 'BP')} for g in GRIDS},
       'drops_pct': {g: {'BRJ': (None if drop(g) is None else round(drop(g), 4)), 'BP': (None if drop(g, 'BP') is None else round(drop(g, 'BP'), 4))} for g in GRIDS},
       'V20_reference_drop_pct': round(d_v20, 4),
       'verdict': {'C1': checks['C1_door_quality']['pass'], 'C2_strict': c2['strict_pass'], 'C3': all(v['pass'] for v in c3.values()),
                   'C4': checks['C4_zero_skip_negative']['pass'], 'C5': checks['C5_bp_negative_control']['pass'],
                   'C6': checks['C6_quality_no_regression']['pass'], 'C7': checks['C7_position_single_variable']['pass'],
                   'H2_posthoc': checks['H2_reanchored_model_posthoc']['all_within_1pt']}}
import subprocess
out['ts_utc_plus8'] = subprocess.run(['date', '-Iseconds'], capture_output=True, text=True).stdout.strip()
json.dump(out, open(D / 'compare-r440.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('== 预注册判据 ==')
for k in ('C1_door_quality', 'C2_A_denominator', 'C3_prediction_within_3pt', 'C4_zero_skip_negative', 'C5_bp_negative_control', 'C6_quality_no_regression', 'C7_position_single_variable'):
    v = checks[k]
    ok = v['pass'] if 'pass' in v else all(x['pass'] for x in v.values())
    print(f'  {k:32} {"PASS" if ok else "FAIL"}')
print('  C2 细节:', json.dumps({k: v for k, v in c2.items() if k != 'strict_pass'}, ensure_ascii=False)[:520])
print('  C3 细节:', json.dumps(c3, ensure_ascii=False)[:600])
print('== 事后校核 ==')
print('  H1 δ(实测量):', {g: v['delta_emp_tok'] for g, v in checks['H1_delta_law_posthoc'].items()})
for g, v in checks['H2_reanchored_model_posthoc'].items():
    if isinstance(v, dict):
        print(f"  H2 {g:4}: pred={v['pred_drop_pct']} measured={v['measured_drop_pct']} dev={v['dev_pt']}pt")
print('  H2 all_within_1pt:', checks['H2_reanchored_model_posthoc']['all_within_1pt'])
print('== 降幅表 ==', json.dumps(out['drops_pct'], ensure_ascii=False), '| V20', out['V20_reference_drop_pct'])
print('verdict:', json.dumps(out['verdict'], ensure_ascii=False))
print('wrote', D / 'compare-r440.json')
