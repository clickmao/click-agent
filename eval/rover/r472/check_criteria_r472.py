#!/usr/bin/env python3
# R472 事后判据分析 (POST-HOC, 明确标记): 预注册判据 C7(判定函数自检) 在执行后判 FAIL。
# 本脚本做三件事, 全部离线纯函数, **不发起任何新 API 调用**:
#   P1 复现 C7 失败原因: 预注册版 CAP 分支阈值 (r_MID <= 0.65) 对「cap=2048 且 mid 前缀=2600」不可达 => 分支逻辑缺陷
#   P2 修正判定函数 v2: 饱和信号改为「命中量不再随前缀增长」(hit_BIG <= 1.15 x hit_MID) 而非比值阈值
#   P3 用 v2 重跑真实数据与 4 个合成输入, 证明 (a) v2 自检全过 (b) 真实数据在 v1/v2 下同判 NO_CAP (结论不依赖修正)
# 另附 P0: 数据级直接证伪(不依赖任何判定函数) —— 真实观察到的最大 hit 与假设上限的比较。
import collections
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, 'eval', 'rover', 'r472')


def judge_v1(r_small, r_mid, r_big):
    """预注册版 (逐字), 用于复现 C7 失败。"""
    if r_small is None or r_mid is None or r_big is None:
        return 'UNDECIDABLE'
    if r_small < 0.80:
        return 'UNDECIDABLE'
    if r_big >= 0.85 and r_mid >= 0.85:
        return 'NO_CAP'
    if r_big <= 0.65 and r_mid <= 0.65:
        return 'CAP'
    return 'PARTIAL'


def judge_v2(p_small, h_small, p_mid, h_mid, p_big, h_big):
    """修正版(事后): 饱和 = 命中量停止随前缀增长。"""
    if None in (p_small, h_small, p_mid, h_mid, p_big, h_big) or 0 in (p_small, p_mid, p_big):
        return 'UNDECIDABLE'
    r_small = h_small / p_small
    if r_small < 0.80:
        return 'UNDECIDABLE'                      # 小前缀正控失败 ⇒ 机制不活, 不下结论
    if h_big >= 0.85 * p_big and h_mid >= 0.85 * p_mid:
        return 'NO_CAP'                           # 命中随前缀线性
    if h_big <= h_mid * 1.15 and h_big <= 0.65 * p_big:
        return 'CAP'                              # 前缀增长 1.5x 但命中不涨 ⇒ 饱和
    return 'PARTIAL'


def main():
    a = json.load(io.open(os.path.join(OUT, 'asserts-r472.json'), encoding='utf-8'))
    ru = a['raw_usage']

    def u(tag, f):
        v = (ru.get(tag) or {}).get(f)
        return v if isinstance(v, int) else None

    P = {k: u(k + '.cold', 'prompt_tokens') for k in ('SMALL', 'MID', 'BIG')}
    H = {k: u(k + '.warm', 'prompt_cache_hit_tokens') for k in ('SMALL', 'MID', 'BIG')}

    # ── P0 数据级直接证伪 (不依赖判定函数) ──
    cap_hypothesis_upper = 2304   # R469/R470/R471 观察到的饱和上沿
    max_hit = max(v for v in H.values() if v is not None)
    p0 = {
        'observed_warm_hits': H, 'observed_prompt_tokens': P,
        'assumed_cap_upper_bound': cap_hypothesis_upper,
        'max_observed_hit': max_hit,
        'falsified_by_single_observation': max_hit > cap_hypothesis_upper,
        'statement': ('单条观察即证伪: BIG 臂 hit=%d > %d ⇒ 「缓存命中存在约 2.1k 硬上限」为假' % (max_hit, cap_hypothesis_upper)),
        'hit_are_64_aligned': {k: (v % 64 == 0) for k, v in H.items() if v is not None},
        'tail_tokens': {k: (P[k] - H[k]) for k in P},   # 每条 warm 调用的未复用尾部(用户消息+模板)
    }

    # ── P1 复现 C7 失败 ──
    c7_expected = {'synth_cap': 'CAP', 'synth_nocap': 'NO_CAP',
                   'synth_cold_polluted': 'UNDECIDABLE', 'synth_partial': 'PARTIAL'}
    got_v1 = dict(a['checks'][-1]['value'])
    p1 = {
        'v1_synth_results': got_v1, 'expected': c7_expected,
        'first_failure': next((k for k in c7_expected if got_v1.get(k) != c7_expected[k]), None),
        'root_cause': ('cap=2048 且 mid 前缀=2600 ⇒ r_MID=0.788 > 0.65 ⇒ 即使存在 2048 硬上限, v1 的 CAP 分支也不可达'
                       ' ⇒ v1 的 CAP 判定条件与前缀臂尺寸不自洽(阈值设计缺陷, 非数据问题)'),
        'reachability_condition_v1_mid': '需要 P_MID >= 2048/0.65 = 3150 才能触发 CAP 分支',
        'impact_on_real_data': '零: 本轮真实数据命中随前缀线性增长, 根本不进入 CAP 分支',
    }

    # ── P2/P3 v2 自检 + 真实数据同判 ──
    synth_v2 = {
        'synth_cap': judge_v2(600, 580, 2600, 2048, 4000, 2048),
        'synth_nocap': judge_v2(600, 580, 2600, 2560, 4000, 3900),
        'synth_cold_polluted': judge_v2(600, 0, 2600, 2048, 4000, 2048),
        'synth_partial': judge_v2(600, 570, 2600, 2340, 4000, 2800),
    }
    real_v2 = judge_v2(P['SMALL'], H['SMALL'], P['MID'], H['MID'], P['BIG'], H['BIG'])
    real_v1 = judge_v1(H['SMALL'] / P['SMALL'], H['MID'] / P['MID'], H['BIG'] / P['BIG'])
    p3 = {
        'v2_synth_results': synth_v2, 'expected': c7_expected,
        'v2_selfcheck_pass': synth_v2 == c7_expected,
        'real_verdict_v1_prereg': real_v1, 'real_verdict_v2_posthoc': real_v2,
        'verdict_robust_to_criteria_fix': real_v1 == real_v2 == 'NO_CAP',
    }

    # ── P4 机制定律(事后派生): hit == 64 * floor((prompt - c)/64), c = 尾部常数 ──
    # c 由 5 条 warm 调用的不等式约束**交**出: 64*floor((P-c)/64) == hit  <=>  hit <= P-c < hit+64
    warm_pts = [('SMALL.warm', P['SMALL'], H['SMALL']), ('MID.warm', P['MID'], H['MID']),
                ('BIG.warm', P['BIG'], H['BIG']),
                ('BIG.warm2', u('BIG.warm2', 'prompt_tokens'), u('BIG.warm2', 'prompt_cache_hit_tokens')),
                ('BIG.ident', u('BIG.ident', 'prompt_tokens'), u('BIG.ident', 'prompt_cache_hit_tokens'))]
    warm_pts = [t for t in warm_pts if None not in t[1:]]
    c_lo, c_hi = -10**9, 10**9
    for _tag, p, h in warm_pts:
        c_lo = max(c_lo, p - h - 63)   # hit <= P-c  =>  c <= P-hit
        c_hi = min(c_hi, p - h)        # P-c < hit+64 => c > P-hit-64
    cands = [c for c in range(c_lo, c_hi + 1) if all(64 * ((p - c) // 64) == h for _t, p, h in warm_pts)]
    c_star = cands[0] if len(cands) == 1 else None
    p4_rows = [{'tag': t, 'prompt': p, 'hit_actual': h,
                'hit_pred(c_star)': (64 * ((p - c_star) // 64)) if c_star is not None else None,
                'hit_64_aligned': h % 64 == 0, 'tail': p - h} for t, p, h in warm_pts]
    p4 = {
        'law': 'prompt_cache_hit_tokens == 64 * floor((prompt_tokens - c) / 64)',
        'block_size_tokens': 64,
        'c_star_unique': c_star, 'c_intersection_interval': [c_lo, c_hi],
        'points': p4_rows,
        'all_points_match': bool(c_star is not None and all(r['hit_actual'] == r['hit_pred(c_star)'] for r in p4_rows)),
        'note': ('c = 该请求形状下不可复用尾部(聊天模板 + 用户消息)的 token 数; 命中量只由「与历史调用共享的前缀长度」决定, '
                 '精确到 64 token 块; 不存在 ~2k 级上限'),
    }

    out = collections.OrderedDict([
        ('round', 'R472'), ('kind', 'post_hoc_criteria_analysis'),
        ('label', 'POST-HOC: 本文件全部为事后分析, 与预注册判据分开计; 预注册版 C7 判 FAIL 不被覆盖'),
        ('new_api_calls', 0),
        ('P0_data_level_falsification', p0),
        ('P1_prereg_C7_failure_root_cause', p1),
        ('P3_corrected_criteria_and_robustness', p3),
        ('P4_mechanism_law', p4),
        ('posthoc_checks', [
            collections.OrderedDict([('id', 'P0'), ('ok', p0['falsified_by_single_observation']),
                                     ('desc', '数据级直接证伪: 观察最大 hit 5632 > 假设上限 2304 (无需判定函数)')]),
            collections.OrderedDict([('id', 'P1'), ('ok', p1['first_failure'] == 'synth_cap'),
                                     ('desc', '预注册 C7 失败根因定位: CAP 分支阈值与前缀臂尺寸不自洽')]),
            collections.OrderedDict([('id', 'P3'), ('ok', p3['v2_selfcheck_pass'] and p3['verdict_robust_to_criteria_fix']),
                                     ('desc', '修正判据 v2 自检全过 ∧ 真实数据 v1/v2 同判 NO_CAP ⇒ 结论不依赖判据修正')]),
            collections.OrderedDict([('id', 'P4'), ('ok', p4['all_points_match']),
                                     ('desc', '机制定律: 5 条 warm 调用全部满足 hit == 64*floor((prompt-c)/64), c 唯一解')]),
        ]),
        ('verdict', 'NO_CAP'),
        ('verdict_line', '命中随共享前缀线性增长(hit/前缀 = 0.844/0.946/0.969), 不存在约 2.1k 供应商硬上限; 真实流中 2048~2304 的饱和是「共享前缀本身只有 ~2.1k」, 不是上限'),
    ])
    io.open(os.path.join(OUT, 'posthoc-r472.json'), 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print('P0  max_observed_hit =', max_hit, '> assumed 2304 =>', p0['falsified_by_single_observation'])
    print('     hits', H, 'prompts', P, 'tails', p0['tail_tokens'], '64-aligned', p0['hit_are_64_aligned'])
    print('P1  v1 synth =', got_v1, '| first failure =', p1['first_failure'])
    print('P3  v2 synth =', synth_v2, '| selfcheck', p3['v2_selfcheck_pass'], '| real v1', real_v1, 'v2', real_v2)
    print('P4  law:', p4['law'], '| c_star =', c_star, '| interval', p4['c_intersection_interval'])
    for r in p4_rows:
        print('     ', r['tag'], 'prompt', r['prompt'], 'hit', r['hit_actual'], 'pred', r['hit_pred(c_star)'],
              'tail', r['tail'], '64aligned', r['hit_64_aligned'])
    print('ALL POST-HOC CHECKS:', all(c['ok'] for c in out['posthoc_checks']))
    return 0 if all(c['ok'] for c in out['posthoc_checks']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
