#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R449 · 真实流量门判探针裁决器 (预注册判据机检).

输入: probe-r449-real.jsonl + prereg-probe.json + external-validity-gate.json
输出: verdict-probe-r449.json
判据: I1 正控 (网格认可族 >=5/7 判 S), I2 负控 (非认可族 >=9/13 判 P),
      V1: 机械 ack=0/1542 且 D 类假 S 率 >= 0.50 => STATE_DB_CANNOT_IMPROVE_KPI,
      V0: I1 未过 => 读数记 n/a (R380: 没测到 != 失败).
"""
import collections
import json
import math
import pathlib
import sys

R = pathlib.Path('/home/agentuser/AgentFramework/eval/rover/r449')
JSONL = R / 'probe-r449-real.jsonl'
OUT = R / 'verdict-probe-r449.json'


def wilson(k, n, z=1.96):
    if n <= 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - h) / d, 4), round((c + h) / d, 4))


def main():
    rows = [json.loads(l) for l in JSONL.read_text(encoding='utf-8').splitlines() if l.strip()]
    prereg = json.loads((R / 'prereg-probe.json').read_text(encoding='utf-8'))
    gate = json.loads((R / 'external-validity-gate.json').read_text(encoding='utf-8'))
    doc = {'round': 'R449', 'instrument': 'real_gate_probe', 'n_calls': len(rows),
           'cells': {}, 'checks': {}, 'verdict': {}}

    # ---- 分层读数 ----
    for arm in ('real', 'grid'):
        for klass in sorted({r['klass'] for r in rows if r['arm'] == arm}):
            sub = [r for r in rows if r['arm'] == arm and r['klass'] == klass]
            s = sum(1 for r in sub if r['letter'] == 'S')
            p = sum(1 for r in sub if r['letter'] == 'P')
            u = len(sub) - s - p
            deg = sum(1 for r in sub if int(r.get('tok_gen') or 0) >= 512)
            wall = sorted(float(r['wall_s']) for r in sub)
            tok = sorted(int(r.get('tok_eval') or 0) for r in sub)
            doc['cells'][f'{arm}/{klass}'] = {
                'n': len(sub), 'S': s, 'P': p, 'undecided': u,
                'S_rate_decided': round(s / (s + p), 4) if s + p else None,
                'S_rate_decided_wilson95': wilson(s, s + p),
                'S_rate_all_n': round(s / len(sub), 4) if sub else None,
                'degenerate_512': deg,
                'degenerate_rate': round(deg / len(sub), 4) if sub else None,
                'tok_eval_median': tok[len(tok) // 2] if tok else None,
                'wall_s_median': wall[len(wall) // 2] if wall else None,
            }

    # ---- 加权总体 (按真实类权重回算; D 层是过采样) ----
    cc = gate.get('class_counts') or {}
    st = gate.get('stats') or {}
    total_all = sum(int(v) for v in cc.values()) or 1
    wsum = 0.0
    for k, v in cc.items():
        w = int(v) / total_all
        c = doc['cells'].get(f'real/{k}', {})
        if c.get('S_rate_decided') is not None:
            wsum += w * c['S_rate_decided']
    doc['real_weighted_S_rate_decided'] = round(wsum, 4)
    doc['population_weights'] = {k: round(int(v) / total_all, 4) for k, v in cc.items()}

    # ---- 预先注册判据 ----
    g_ack = doc['cells'].get('grid/ack', {})
    g_non = doc['cells'].get('grid/nonack', {})
    i1 = (g_ack.get('S') or 0) >= 5
    i2 = (g_non.get('P') or 0) >= 9
    doc['checks']['I1_positive_control'] = {'pass': i1, 'got': f"{g_ack.get('S')}/{g_ack.get('n')}", 'need': '>=5/7'}
    doc['checks']['I2_negative_control'] = {'pass': i2, 'got': f"{g_non.get('P')}/{g_non.get('n')}", 'need': '>=9/13'}

    ack_all = sum(int((st.get(k) or {}).get('ack') or 0) for k in st)
    elig_all = sum(int((st.get(k) or {}).get('gate_eligible') or 0) for k in st)
    n_all = sum(int((st.get(k) or {}).get('n') or 0) for k in st)
    doc['mechanical'] = {'ack_all': ack_all, 'gate_eligible_all': elig_all, 'n_all': n_all,
                         'per_class': {k: {'ack': v.get('ack'), 'mech_pass': v.get('mech_pass'),
                                           'gate_eligible': v.get('gate_eligible')} for k, v in st.items()}}
    dcell = doc['cells'].get('real/D', {})
    d_false_s = dcell.get('S_rate_decided')
    doc['checks']['V1_condition'] = {
        'd_false_s_rate': d_false_s,
        'threshold': 0.5,
        'mech_ack_zero': (ack_all in (0, 0.0, '0')),
        'fired': bool(ack_all in (0, 0.0, '0') and (d_false_s or 0) >= 0.5),
    }
    if not i1:
        doc['verdict'] = {'code': 'VOID_INSTRUMENT', 'note': 'I1 正控未过 => 本轮读数记 n/a (R380)'}
    elif doc['checks']['V1_condition']['fired']:
        doc['verdict'] = {
            'code': 'STATE_DB_CANNOT_IMPROVE_KPI',
            'note': ('真实流量机械 ack=0 => 现网可跳轮=0; 且判官在真实 D 类(真工作指令)上假 S 率 %.2f >= 0.50, '
                     '退化率 %.2f => 「去掉 Ack 结构条件让 r1 独判」会把真诉求跳成空话(与 R434 失效模式一致)' % (
                         d_false_s or 0, dcell.get('degenerate_rate') or 0)),
            'consequence': '远端降幅在真实分布上无实现路径 => 结案 R449 该通道, 回归主线',
        }
    else:
        doc['verdict'] = {'code': 'NEEDS_EQUIVALENCE_EXPERIMENT', 'note': 'D 类假 S 率 <0.50 且机械 ack=0 => 需用户裁定是否进入等价性实验'}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
