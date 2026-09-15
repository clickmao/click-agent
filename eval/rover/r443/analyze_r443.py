#!/usr/bin/env python3
"""R443 判定器 — ① 本地 r1 成本 **tokenizer 真值**化 ② 「被跳轮不回放」单变量消融。

数据源（全部新真机档案; 外部真值两条 = 桩侧 calls + 产品遥测 promise 区）:
  * `verdict-{A,BRJ,BRJRP}-M20-s1.json` —— 远端真值 (G/J tokens、逐轮、质量计数)
  * `run-{arm}-M20-s1/data/telemetry/host.jsonl` —— 本地 r1 真值:
      local_turn_gate{tokens_evaluated, prompt_new, gen_tokens, cache_n, gate_prompt_len, raw_len}
      correction_judge{source, tokens, tokens_evaluated, prompt_new, gen_tokens}
      local_gate_skip_history{persisted_chars, would_be_chars, dropped_chars, replay_skipped}

预注册判据（见 docs/plans/v0.63.0-r443-local-token-truth-and-replay-ablation.md）:
  D1 记账恒等 tokens_evaluated == prompt_new + cache_n (local_turn_gate); 缺字段记 n/a 不记 0
  D2 真值/折算比 (预测: 真值 ≥ chars/2 ⇒ R442 口径偏乐观/偏保守需按方向说明)
  D3 同网格单变量 Δ(BRJRP−BRJ) ≈ R442 离线分解的 4830.5 tok (±20%)
  D4 默认臂逐轮零回归 vs R441 归档 (Δtot=0 且逐轮 Δ=0)
  D5 replay 标记可机检 (BRJRP: replay_skipped=1 ∧ dropped_chars=0; BRJ: =0 ∧ >0)
  D6 ρ 的 token 影响 = micro_step.tokens 恒 0
"""
import json
import pathlib
import sys

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
D = ROOT / 'eval/rover/r443'
ARCH_R441 = ROOT / 'eval/rover/r441'
NS = '-s1'
GRID = 'M20'
TOL_D3 = 0.20


def load(p):
    return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))


def telemetry(arm):
    p = D / f'run-{arm}-{GRID}{NS}' / 'data' / 'telemetry' / 'host.jsonl'
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding='utf-8-sig').splitlines():
        ln = ln.strip()
        if ln:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    return out


def kv(r):
    return r.get('kv') or {}


def i_(v, dflt=None):
    try:
        return int(v)
    except (TypeError, ValueError):
        return dflt


def part0_prov():
    out = {}
    for a in ('A', 'BRJ', 'BRJRP'):
        v = load(D / f'verdict-{a}-{GRID}{NS}.json')
        out[a] = {k: v.get(k) for k in ('arm', 'grid', 'ns', 'bin_sha', 'calls_total', 'tokens_total', 'G_tokens', 'J_tokens',
                                        'fn_n', 'fp_n', 'accuracy', 'r1_skips', 'r1_passes', 'gate_r1_n', 'gate_mech_n',
                                        'judge_local_tokens', 'judge_remote_fallback_n', 'attribution_ok')}
    return out


def part1_identity(arm):
    """D1: 记账恒等 (真值字段自洽性) — fail-closed 计数, 缺字段记 n/a。"""
    rows = telemetry(arm)
    g = [kv(r) for r in rows if r.get('point') == 'local_turn_gate']
    j = [kv(r) for r in rows if r.get('point') == 'correction_judge']
    res = {'gate_rows': len(g), 'gate_r1_rows': 0, 'gate_identity_checked': 0, 'gate_identity_violations': [],
           'gate_missing_cache_n': 0, 'gate_sentinel_neg1': 0,
           'judge_rows': len(j), 'judge_local_rows': 0, 'judge_missing_cache_n': 0, 'judge_identity_violations': []}
    for k in g:
        ev, nw, cn = i_(k.get('tokens_evaluated')), i_(k.get('prompt_new')), i_(k.get('cache_n'))
        if ev is None or ev < 0:
            res['gate_sentinel_neg1'] += 1
            continue
        res['gate_r1_rows'] += 1
        if cn is None or nw is None:
            res['gate_missing_cache_n'] += 1
            continue
        res['gate_identity_checked'] += 1
        if ev != nw + cn:
            res['gate_identity_violations'].append({'turn': k.get('turn'), 'tokens_evaluated': ev, 'prompt_new': nw, 'cache_n': cn})
    for k in j:
        if k.get('source') != 'local':
            continue
        res['judge_local_rows'] += 1
        ev, nw = i_(k.get('tokens_evaluated')), i_(k.get('prompt_new'))
        if ev is None or ev < 0:
            continue
        cn = i_(k.get('cache_n'))
        if cn is None or nw is None:
            res['judge_missing_cache_n'] += 1
            continue
        if ev != nw + cn:
            res['judge_identity_violations'].append({'tokens_evaluated': ev, 'prompt_new': nw, 'cache_n': cn})
    return res


def part2_truth_vs_estimate(arm):
    """D2: 真值 vs 字符/2 折算 (逐臂; R442 口径的误差实测)。"""
    rows = telemetry(arm)
    g = [kv(r) for r in rows if r.get('point') == 'local_turn_gate']
    j = [kv(r) for r in rows if r.get('point') == 'correction_judge' and kv(r).get('source') == 'local']
    gp_truth = sum(i_(k.get('tokens_evaluated'), 0) for k in g if (i_(k.get('tokens_evaluated'), -1) or -1) >= 0)
    gg_truth = sum(i_(k.get('gen_tokens'), 0) for k in g if (i_(k.get('tokens_evaluated'), -1) or -1) >= 0)
    gp_chars = sum(i_(k.get('gate_prompt_len'), 0) for k in g)
    gg_chars = sum(i_(k.get('raw_len'), 0) for k in g)
    jp_truth = sum(i_(k.get('tokens_evaluated'), 0) for k in j if (i_(k.get('tokens_evaluated'), -1) or -1) >= 0)
    jg_truth = sum(i_(k.get('gen_tokens'), 0) for k in j if (i_(k.get('gen_tokens'), -1) or -1) >= 0)
    jp_chars = sum(i_(k.get('prompt_len'), 0) for k in j)
    r = {}
    r['gate_prompt'] = {'n': len([k for k in g if (i_(k.get('tokens_evaluated'), -1) or -1) >= 0]), 'truth': gp_truth,
                        'est_chars_over_2': round(gp_chars / 2, 1), 'chars': gp_chars,
                        'truth_over_est': round(gp_truth / (gp_chars / 2), 4) if gp_chars else None}
    r['gate_gen'] = {'truth': gg_truth, 'est_chars_over_2': round(gg_chars / 2, 1), 'chars': gg_chars,
                     'truth_over_est': round(gg_truth / (gg_chars / 2), 4) if gg_chars else None}
    r['judge_prompt'] = {'n': len(j), 'truth': jp_truth, 'est_chars_over_2': round(jp_chars / 2, 1), 'chars': jp_chars,
                         'truth_over_est': round(jp_truth / (jp_chars / 2), 4) if jp_chars else None}
    r['judge_gen'] = {'truth': jg_truth}
    # R442 口径 (chars/2) 与本轮真值口径的对照
    r['local_total_r442_style'] = round((gp_chars + gg_chars) / 2 + jg_truth, 1)
    r['local_total_truth'] = gp_truth + gg_truth + jp_truth + jg_truth
    if r['local_total_r442_style']:
        r['truth_over_r442'] = round(r['local_total_truth'] / r['local_total_r442_style'], 4)
    return r


def part3_drops(p0, arm='BRJ'):
    """口径三档: 真值本地成本入账。"""
    A, B = p0['A'], p0[arm]
    la = 0.0  # A 臂 turn_gate=false ∧ relation_judge=false ⇒ 无本地 r1
    lb = cv_truth = part2_truth_vs_estimate(arm)
    out = {}
    out['D_remote'] = round(100 * (1 - B['G_tokens'] / A['G_tokens']), 4)
    lb_est = cv_truth['local_total_r442_style']
    lb_truth = cv_truth['local_total_truth']
    out['D_remote_plus_local_r442_style'] = round(100 * (1 - (B['G_tokens'] + lb_est) / (A['G_tokens'] + la)), 4)
    out['D_remote_plus_local_truth'] = round(100 * (1 - (B['G_tokens'] + lb_truth) / (A['G_tokens'] + la)), 4)
    out['local_B_r442_style'] = lb_est
    out['local_B_truth'] = lb_truth
    out['turn_cost_truth'] = round(lb_truth / 20, 1)
    out['break_even_k_over_N'] = round((lb_truth / 20) / ((A['G_tokens'] - B['G_tokens']) / 7), 4) if B['r1_skips'] else None
    return out


def part4_d4_zero_regression():
    """D4: 默认臂 (BRJ) 与 R441 归档逐轮零回归 (行为=纯遥测加性 ⇒ 必须逐位相同)。"""
    a = load(ARCH_R441 / 'verdict-BRJ-M20.json')
    b = load(D / f'verdict-BRJ-{GRID}{NS}.json')
    pa = {t['turn']: t for t in a.get('per_turn', [])}
    pb = {t['turn']: t for t in b.get('per_turn', [])}
    diffs = []
    for t in sorted(set(pa) | set(pb)):
        ga, gb = pa.get(t, {}).get('G_tokens'), pb.get(t, {}).get('G_tokens')
        if ga != gb:
            diffs.append({'turn': t, 'r441': ga, 'r443': gb, 'delta': (gb - ga) if (ga is not None and gb is not None) else None})
    return {'total_r441': a.get('G_tokens'), 'total_r443': b.get('G_tokens'),
            'total_delta': (b.get('G_tokens') - a.get('G_tokens')) if a.get('G_tokens') and b.get('G_tokens') else None,
            'per_turn_diffs': diffs, 'turns_compared': len(set(pa) | set(pb)),
            'zero_regression': (not diffs) and a.get('G_tokens') == b.get('G_tokens')}


def part5_d3_ablation():
    """D3: 同网格单变量 Δ = BRJRP − BRJ (唯一变量 = 回放被跳轮内联块)。"""
    b = load(D / f'verdict-BRJ-{GRID}{NS}.json')
    r = load(D / f'verdict-BRJRP-{GRID}{NS}.json')
    pa = {t['turn']: t for t in b.get('per_turn', [])}
    pr = {t['turn']: t for t in r.get('per_turn', [])}
    per = []
    for t in sorted(set(pa) | set(pr)):
        ga, gr = pa.get(t, {}).get('G_tokens'), pr.get(t, {}).get('G_tokens')
        per.append({'turn': t, 'brj': ga, 'brjrp': gr, 'delta': (gr - ga) if (ga is not None and gr is not None) else None})
    delta = (r['G_tokens'] - b['G_tokens']) if (b.get('G_tokens') and r.get('G_tokens')) else None
    ref = 4830.5
    return {'brj_total': b.get('G_tokens'), 'brjrp_total': r.get('G_tokens'), 'delta_total': delta,
            'r442_offline_ref_4830_5': ref,
            'ratio_vs_ref': round(delta / ref, 4) if delta is not None else None,
            'within_tol_20pct': (delta is not None and abs(delta - ref) <= TOL_D3 * ref),
            'per_turn': per, 'r1_skips_brj': b.get('r1_skips'), 'r1_skips_brjrp': r.get('r1_skips'),
            'quality_brj': {k: b.get(k) for k in ('fn_n', 'fp_n', 'accuracy')},
            'quality_brjrp': {k: r.get(k) for k in ('fn_n', 'fp_n', 'accuracy')},
            'attribution_ok_brjrp': r.get('attribution_ok')}


def part6_d5_markers():
    out = {}
    for arm in ('BRJ', 'BRJRP'):
        rows = [kv(x) for x in telemetry(arm) if x.get('point') == 'local_gate_skip_history']
        out[arm] = {'n': len(rows),
                    'replay_1': sum(1 for k in rows if k.get('replay_skipped') == '1'),
                    'replay_0': sum(1 for k in rows if k.get('replay_skipped') == '0'),
                    'dropped_sum': sum(i_(k.get('dropped_chars'), 0) for k in rows),
                    'persisted_sum': sum(i_(k.get('persisted_chars'), 0) for k in rows),
                    'would_be_sum': sum(i_(k.get('would_be_chars'), 0) for k in rows)}
    return out


def part6b_confounder():
    """路径后缀混淆量实测: A 臂对 (R441 无 NS vs R443 -s1) 逐轮 + 总额差 ⇒ 每调用平均偏移。"""
    a = load(ARCH_R441 / 'verdict-A-M20.json')
    b = load(D / f'verdict-A-{GRID}{NS}.json')
    pa = {t['turn']: t for t in a.get('per_turn', [])}
    pb = {t['turn']: t for t in b.get('per_turn', [])}
    diffs = []
    for t in sorted(set(pa) | set(pb)):
        ga, gb = pa.get(t, {}).get('G_tokens'), pb.get(t, {}).get('G_tokens')
        if ga != gb:
            diffs.append({'turn': t, 'r441': ga, 'r443': gb, 'delta': (gb - ga) if (ga is not None and gb is not None) else None})
    n_calls = b.get('G_calls') or 0
    d = (b['G_tokens'] - a['G_tokens']) if (a.get('G_tokens') and b.get('G_tokens')) else None
    return {'call_total_r441': a.get('G_calls'), 'call_total_r443': n_calls,
            'total_r441': a.get('G_tokens'), 'total_r443': b.get('G_tokens'), 'total_delta': d,
            'delta_per_call': round(d / n_calls, 4) if (d is not None and n_calls) else None,
            'per_turn_diffs': diffs, 'turns_compared': len(set(pa) | set(pb))}


def part4b_zero_regression_no_ns():
    """D4b: 无 NS 同名臂 (新二进制) vs R441 归档 (旧二进制) 逐轮逐位 —— 唯一干净零回归判据。"""
    a = load(ARCH_R441 / 'verdict-BRJ-M20.json')
    b = load(D / 'verdict-BRJ-M20.json')
    pa = {t['turn']: t for t in a['per_turn']}; pb = {t['turn']: t for t in b['per_turn']}
    diffs = []
    for t in sorted(set(pa) & set(pb)):
        x, y = pa[t], pb[t]
        if (x.get('G_tokens'), x.get('G_calls'), x.get('actual'), x.get('mech')) != \
           (y.get('G_tokens'), y.get('G_calls'), y.get('actual'), y.get('mech')):
            diffs.append({'turn': t, 'r441': x.get('G_tokens'), 'r443': y.get('G_tokens')})
    return {'r441_bin': a.get('bin_sha'), 'r443_bin': b.get('bin_sha'),
            'r441_total': a.get('G_tokens', 0) + a.get('J_tokens', 0), 'r443_total': b.get('G_tokens', 0) + b.get('J_tokens', 0),
            'turns_compared': len(set(pa) & set(pb)), 'per_turn_diffs': diffs,
            'zero_regression': (not diffs) and (a.get('G_tokens') == b.get('G_tokens')),
            'quality': {'r441': [a.get('fn_n'), a.get('fp_n'), a.get('accuracy')], 'r443': [b.get('fn_n'), b.get('fp_n'), b.get('accuracy')]},
            'judge_local_tokens': [a.get('judge_local_tokens'), b.get('judge_local_tokens')],
            'attribution': [a.get('attribution_ok'), b.get('attribution_ok')]}


def part7_d6_rho():
    out = {}
    for arm in ('A', 'BRJ', 'BRJRP'):
        rows = [kv(x) for x in telemetry(arm) if x.get('point') == 'micro_step']
        out[arm] = {'n': len(rows), 'tokens': sorted({i_(k.get('tokens'), 0) for k in rows}),
                    'ms': sorted({i_(k.get('ms'), 0) for k in rows})}
    return out


def main():
    p0 = part0_prov()
    res = {'ns': NS, 'grid': GRID, 'prov': p0}
    res['D1_identity'] = {a: part1_identity(a) for a in ('A', 'BRJ', 'BRJRP')}
    res['D2_truth_vs_estimate'] = {a: part2_truth_vs_estimate(a) for a in ('BRJ', 'BRJRP')}
    res['D2b_path_confounder'] = part6b_confounder()
    res['D3_drops_truth'] = part3_drops(p0)
    res['D4_zero_regression_vs_r441'] = part4_d4_zero_regression()
    res['D4b_zero_regression_no_ns'] = part4b_zero_regression_no_ns()
    res['D5_ablation_single_variable'] = part5_d3_ablation()
    res['D6_replay_markers'] = part6_d5_markers()
    res['D7_rho_micro_step'] = part7_d6_rho()
    out = D / 'verdict-r443-analysis.json'
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')

    print('=== D0 档案 ===')
    for a, v in p0.items():
        print(f"  {a:6s} tot={v['tokens_total']} G={v['G_tokens']} J={v['J_tokens']} skips={v['r1_skips']} "
              f"fn={v['fn_n']} fp={v['fp_n']} acc={v['accuracy']} bin={str(v['bin_sha'])[:12]}")
    print('=== D1 记账恒等 ===')
    for a in ('A', 'BRJ', 'BRJRP'):
        d1 = res['D1_identity'][a]
        print(f"  {a:6s} gate_rows={d1['gate_rows']} r1_rows={d1['gate_r1_rows']} checked={d1['gate_identity_checked']} "
              f"违规={len(d1['gate_identity_violations'])} 缺cache_n={d1['gate_missing_cache_n']} sentinel(-1)={d1['gate_sentinel_neg1']} "
              f"| judge_local={d1['judge_local_rows']} 违规={len(d1['judge_identity_violations'])}")
    print('=== D2 真值 vs 字符/2 ===')
    for a in ('BRJ', 'BRJRP'):
        t = res['D2_truth_vs_estimate'][a]
        print(f"  {a:6s} gate_prompt truth={t['gate_prompt']['truth']} est={t['gate_prompt']['est_chars_over_2']} "
              f"ratio={t['gate_prompt']['truth_over_est']} | gate_gen truth={t['gate_gen']['truth']} est={t['gate_gen']['est_chars_over_2']} "
              f"ratio={t['gate_gen']['truth_over_est']} | judge_prompt truth={t['judge_prompt']['truth']} est={t['judge_prompt']['est_chars_over_2']} "
              f"ratio={t['judge_prompt']['truth_over_est']} | judge_gen truth={t['judge_gen']['truth']}")
        print(f"         本地合计: R442式={t['local_total_r442_style']} 真值={t['local_total_truth']} 真值/R442={t.get('truth_over_r442')}")
    print('=== D3 口径三档 (M20) ===')
    for k, v in res['D3_drops_truth'].items():
        print(f"  {k} = {v}")
    print('=== D4 默认臂零回归 (vs R441) ===')
    d4 = res['D4_zero_regression_vs_r441']
    print(f"  r441={d4['total_r441']} r443={d4['total_r443']} Δ={d4['total_delta']} 逐轮差异数={len(d4['per_turn_diffs'])} "
          f"比较轮数={d4['turns_compared']} 零回归={d4['zero_regression']}")
    print('=== D5 单变量消融 ===')
    d5 = res['D5_ablation_single_variable']
    print(f"  BRJ={d5['brj_total']} BRJRP={d5['brjrp_total']} Δ={d5['delta_total']} ref(R442离线)={d5['r442_offline_ref_4830_5']} "
          f"ratio={d5['ratio_vs_ref']} 20%内={d5['within_tol_20pct']}")
    print(f"  质量 BRJ fn={d5['quality_brj']} BRJRP fn={d5['quality_brjrp']} 归属ok={d5['attribution_ok_brjrp']}")
    print('=== D6 replay 标记 ===')
    for a, v in res['D6_replay_markers'].items():
        print(f"  {a:6s} n={v['n']} replay1={v['replay_1']} replay0={v['replay_0']} dropped_sum={v['dropped_sum']} "
              f"persisted_sum={v['persisted_sum']} would_be_sum={v['would_be_sum']}")
    print('=== D7 ρ (micro_step) ===')
    for a, v in res['D7_rho_micro_step'].items():
        print(f"  {a:6s} n={v['n']} tokens={v['tokens']} ms={v['ms']}")
    print('[written]', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
