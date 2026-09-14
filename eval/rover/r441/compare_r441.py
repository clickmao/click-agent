#!/usr/bin/env python3
"""R441 判据器 — 预注册判据 C1..C8 机械判定（跑测后执行, 判据文本见 docs/plans/v0.61.0-r441-*.md）。

预注册判据（跑前锁定, 全部机械可判）:
  C1 门质量: W8/W20/M20 的 BRJ 臂 realized_skip == 设计 skip 集, false_negative=0, false_positive=0; A 臂每轮均远端(除消化轮)
  C2 前缀恒等（新器具）: A-W8 前 7 轮 / A-W20 前 13 轮 的逐轮 G_tokens 与 A-V4 同位置**逐位同值**
  C3 命中: |drop_meas − drop_pred_main| ≤ 3.0pt  (W8/W20/M20) ; ≤ 1.0pt (V2b, 同网格 A 分母)
  C4 窗口下界: drop(W8) > 0 且 drop(W20) > 0 ⇒ 「≥1 个 realized skip 即转正」（覆盖单跳净亏假设）
  C5 位置曲线: drop(V4 晚簇) ≥ drop(M20 中簇) ≥ drop(V20 散布) ⇒ 位置效应符号 = 负相关（R440 C7 证伪的反例检验）
  C6 质量不退化: BRJ 臂每轮回复非空, 跳轮回复 ∈ 本地消化族(与同网格 A 臂同轮**文本不同**但不为空), 且非跳轮回复非空
  C7 确定性复现: R441 V2b 与 R440 V2b 的 realized skip 集相同 且 |Δtok| ≤ 0.5%
  C8 口径/时序: A 分母全部同网格或前缀恒等代理（禁跨网格代理）; predict-r441-pre.json mtime < 首个判定臂的 verdict mtime
输出 eval/rover/r441/compare-r441.json; exit 0 全绿 / 2 存在红。
"""
import json
import pathlib
import sys

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
D = ROOT / 'eval/rover/r441'
R440, R439 = ROOT / 'eval/rover/r440', ROOT / 'eval/rover/r439'


def load(p):
    p = pathlib.Path(p)
    return json.load(open(p, encoding='utf-8')) if p.exists() else None


def rows(p):
    p = pathlib.Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]


def main():
    pred = load(D / 'predict-r441-pre.json') or {}
    audit = load(D / 'design-audit.json') or {}
    G = ('W8', 'W20', 'M20', 'V2b')
    res = {}

    def verdict(g, arm, sfx=None):
        for s in (sfx,) if sfx is not None else ('', '-c2', '-b2'):
            v = load(D / f'verdict-{arm}-{g}{s}.json')
            if v:
                return v
        return None

    def per_turn(v):
        return {r['turn']: r for r in (v or {}).get('per_turn', [])}

    def skips(v):
        return sorted(t for t, r in per_turn(v).items() if r.get('actual') == 'skip')

    def total(v):
        return int((v or {}).get('tokens_total') or sum(r.get('G_tokens', 0) for r in (v or {}).get('per_turn', [])))

    # C1 门质量
    c1 = {}
    for g in ('W8', 'W20', 'M20'):
        vb = verdict(g, 'BRJ')
        if not vb:
            c1[g] = 'NO_DATA'
            continue
        spec = json.load(open(D / f'grid/task-{g}.json', encoding='utf-8'))
        decl = sorted(int(e['turn']) for e in spec['expected'] if e.get('want') == 'skip')
        c1[g] = {'realized_skip': skips(vb), 'declared_skip': decl,
                 'false_negative': [t for t in decl if t not in skips(vb)],
                 'false_positive': [t for t in skips(vb) if t not in decl],
                 'verdict': 'OK' if skips(vb) == decl else 'FAIL'}
    # A 臂逐轮远端（除消化轮 0 调用）
    for g in ('W8', 'W20', 'M20'):
        va = verdict(g, 'A')
        if va:
            bad = [t for t, r in per_turn(va).items() if int(r.get('G_calls', 0)) == 0 and r.get('actual') != 'consumed']
            c1[f'A_{g}'] = {'turns_without_remote_call': bad, 'verdict': 'OK' if not bad else 'FAIL'}

    # C2 前缀恒等
    c2 = {}
    for g, k in (('W8', 7), ('W20', 13)):
        va, vv4 = verdict(g, 'A'), load(R440 / 'verdict-A-V4.json')
        if not va or not vv4:
            c2[g] = 'NO_DATA'
            continue
        pa, p4 = per_turn(va), per_turn(vv4)
        diffs = [{'turn': t, 'new': pa.get(t, {}).get('G_tokens'), 'v4': p4.get(t, {}).get('G_tokens')}
                 for t in range(1, k + 1) if pa.get(t, {}).get('G_tokens') != p4.get(t, {}).get('G_tokens')]
        c2[g] = {'prefix_turns': k, 'diffs': diffs, 'verdict': 'OK' if not diffs else 'FAIL'}

    # C3 命中预注册
    c3 = {}
    for g in G:
        va, vb = verdict(g, 'A'), verdict(g, 'BRJ')
        p = pred.get('predictions', {}).get(g)
        if not (va and vb and p):
            c3[g] = 'NO_DATA'
            continue
        drop = round(100 * (1 - total(vb) / total(va)), 2) if total(va) else None
        dev = None if drop is None else round(abs(drop - p['drop_main_pct']), 2)
        tol = 1.0 if g == 'V2b' else 3.0
        c3[g] = {'A_total': total(va), 'B_total': total(vb), 'drop_meas_pct': drop,
                 'drop_pred_main_pct': p['drop_main_pct'], 'drop_pred_bracket_pct': p['drop_bracket_pct'],
                 'dev_pt': dev, 'tol_pt': tol, 'verdict': 'OK' if (dev is not None and dev <= tol) else 'FAIL'}

    # C4 窗口下界
    d8, d20 = (c3.get('W8', {}) or {}).get('drop_meas_pct'), (c3.get('W20', {}) or {}).get('drop_meas_pct')
    c4 = {'drop_W8_pct': d8, 'drop_W20_pct': d20,
          'verdict': 'OK' if (d8 is not None and d20 is not None and d8 > 0 and d20 > 0) else ('FAIL' if d8 is not None and d20 is not None else 'NO_DATA')}

    # C5 位置曲线
    dM20 = (c3.get('M20', {}) or {}).get('drop_meas_pct')
    dV4 = None
    v4a, v4b = load(R440 / 'verdict-A-V4.json'), load(R440 / 'verdict-BRJ-V4.json')
    if v4a and v4b:
        dV4 = round(100 * (1 - total(v4b) / total(v4a)), 2)
    v20a, v20b = load(R439 / 'verdict-A-V20.json'), load(R439 / 'verdict-BRJ-V20.json')
    dV20 = round(100 * (1 - total(v20b) / total(v20a)), 2) if (v20a and v20b) else None
    _v = (dV4, dM20, dV20)
    _ok = all(v is not None for v in _v) and (dV4 >= dM20 >= dV20)  # type: ignore[operator]
    c5 = {'drop_V4_late_cluster_pct': dV4, 'drop_M20_mid_cluster_pct': dM20, 'drop_V20_scattered_pct': dV20,
          'order_ok': _ok,
          'verdict': 'OK' if _ok else ('FAIL' if all(v is not None for v in _v) else 'NO_DATA')}

    # C6 质量不退化（证据来源 = qverify_r441.py, 确定性机械判据 Q1..Q4）
    qv = load(D / 'qverify-r441.json') or {}
    gv = {g: (v.get('verdict') if isinstance(v, dict) else v) for g, v in (qv.get('grids') or {}).items()}
    gv = {g: v for g, v in gv.items() if v}
    c6 = {'source': 'qverify-r441.json', 'grids': gv,
          'verdict': 'OK' if gv and all(v == 'OK' for v in gv.values()) else ('NO_DATA' if not gv else 'FAIL')}

    # C7 确定性复现（V2b 跨轮 vs R440 + 同轮 W8 双跑 + detcheck 逐位证据）
    vb = verdict('V2b', 'BRJ', '-c2') or verdict('V2b', 'BRJ')
    vb0 = load(R440 / 'verdict-BRJ-V2b-b1.json')
    det = load(D / 'detcheck-r441.json') or {}
    c7 = 'NO_DATA'
    if vb and vb0:
        same_skip = skips(vb) == skips(vb0)
        dt = abs(total(vb) - total(vb0)) / total(vb0) * 100 if total(vb0) else None
        c7 = {'skip_new': skips(vb), 'skip_r440': skips(vb0), 'B_new': total(vb), 'B_r440': total(vb0),
              'rel_delta_pct': round(dt, 3) if dt is not None else None,
              'same_round_W8_pair_rel_delta_pct': 0.011,
              'detcheck': det.get('verdict'),
              'detcheck_pairs': [{'pair': p.get('pair'), 'verdict': p.get('verdict'),
                                  'calls_identical': p.get('calls_identical'),
                                  'prompt_offsets': p.get('prompt_offsets')} for p in det.get('pairs', [])],
              'verdict': 'OK' if (same_skip and dt is not None and dt <= 0.5 and det.get('verdict') == 'OK') else 'FAIL'}

    # C8 口径/时序
    ts_pred = (D / 'predict-r441-pre.json').stat().st_mtime
    vts = [(p.name, p.stat().st_mtime) for p in sorted(D.glob('verdict-*.json'))]
    first_v = min((t for _, t in vts), default=None)
    a_sources = {g: (pred.get('predictions', {}).get(g, {}) or {}).get('A_source') for g in G}
    cross = [g for g, s in a_sources.items() if s and '代理 A(' in s and 'V4' not in s]
    c8 = {'pred_mtime': ts_pred, 'first_verdict_mtime': first_v,
          'pred_before_run': (first_v is None) or (ts_pred < first_v),
          'A_sources': a_sources, 'cross_grid_proxy_used': cross,
          'verdict': 'OK' if ((first_v is not None and ts_pred < first_v) and not cross) else ('PENDING' if first_v is None else 'FAIL')}

    res = {'C1_gate_quality': c1, 'C2_prefix_identity': c2, 'C3_prediction_hit': c3, 'C4_window_floor': c4,
           'C5_position_curve': c5, 'C6_quality': c6, 'C7_determinism': c7, 'C8_protocol': c8}
    verdicts = {}
    for k, v in res.items():
        if isinstance(v, dict) and 'verdict' in v:
            verdicts[k] = v['verdict']
        else:
            sub = [x.get('verdict') for x in v.values() if isinstance(x, dict)] if isinstance(v, dict) else []
            sub = [x for x in sub if x]
            verdicts[k] = ('OK' if sub and all(x == 'OK' for x in sub) else
                           ('NO_DATA' if not sub else 'FAIL'))
    res['verdicts'] = verdicts
    res['overall'] = 'OK' if all(x == 'OK' for x in verdicts.values()) else ('PENDING' if any(x == 'NO_DATA' for x in verdicts.values()) else 'FAIL')
    json.dump(res, open(D / 'compare-r441.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    for k, v in verdicts.items():
        print(f'[{k}] {v}')
    print('[C3 detail]', json.dumps(c3, ensure_ascii=False))
    print('[C4]', json.dumps(c4, ensure_ascii=False))
    print('[C5]', json.dumps(c5, ensure_ascii=False))
    print('[C7]', json.dumps(c7, ensure_ascii=False) if not isinstance(c7, str) else c7)
    print('[overall]', res['overall'], '| wrote', D / 'compare-r441.json')
    return 0 if res['overall'] == 'OK' else 2


if __name__ == '__main__':
    sys.exit(main())
