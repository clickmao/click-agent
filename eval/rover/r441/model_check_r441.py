#!/usr/bin/env python3
"""R441 模型校验（**事后**器具，非预注册）— 用**同网格实测 A** 作分母，检验两参数律能否逐位复现 BRJ 臂远端总量。

为什么需要它: 预注册预测器（predict_r441-pre.json）在 W8 上把代理 A 未按 N 截断 ⇒ 分母用了 V4 全长 61281（应为 17260）⇒ 注册降幅 4.13% 与实测 13.77% 不符。
本器具把口径修正后**重算**（明确标 post-hoc），并逐轮做残差分解，用于判定「模型式」本身是否成立（与「注册预测是否命中」解耦）。

输入: eval/rover/r441/verdict-{A,BRJ}-<g>.json（同网格实测）, predict-r441-pre.json（取 δ/ρ/λ/m 派生值）
输出: eval/rover/r441/model-check-r441.json
"""
import json
import pathlib
import sys

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
D = ROOT / 'eval/rover/r441'
GRIDS = ('W8', 'W20', 'M20', 'V2b')


def load(p):
    p = pathlib.Path(p)
    return json.load(open(p, encoding='utf-8')) if p.exists() else None


def main():
    pred = load(D / 'predict-r441-pre.json')
    assert pred, '缺少 predict-r441-pre.json（模型参数派生源）'
    model = pred['model']
    delta = int(model['delta_per_turn'])
    rho = int(model['rho_skip_residual']['primary'])
    lam = float(model['lambda_removal_calibration']['lam'])
    m = {int(k): v for k, v in model['block_mass_medians'].items()}
    out = {'round': 'r441', 'kind': 'POST_HOC (口径修正; 非预注册)', 'params': {'delta': delta, 'rho_primary': rho, 'lambda': lam},
           'grids': {}}
    for g in GRIDS:
        va, vb = load(D / f'verdict-A-{g}.json'), load(D / f'verdict-BRJ-{g}.json')
        if not (va and vb):
            out['grids'][g] = 'NO_DATA'
            continue
        pa = {r['turn']: r for r in va['per_turn']}
        pb = {r['turn']: r for r in vb['per_turn']}
        S = sorted(t for t, r in pb.items() if r.get('actual') == 'skip')
        A_tot, B_meas = int(va['tokens_total']), int(vb['tokens_total'])
        b_pred, resid_rows, removed = 0.0, [], 0.0
        for t in sorted(pa):
            a = int(pa[t].get('G_tokens', 0))
            if t in S:
                b_pred += rho
                contrib = rho - a
            else:
                b_pred += a + delta * (1 if int(pa[t].get('G_calls', 0)) > 0 else 0)
                contrib = delta * (1 if int(pa[t].get('G_calls', 0)) > 0 else 0)
            resid_rows.append({'turn': t, 'A': a, 'B_meas': int(pb.get(t, {}).get('G_tokens', 0)), 'delta_contrib': contrib})
        for t in S:  # 移除项: 跳轮的内联块不再出现在后续轮 prompt 中
            later = [i for i in sorted(pa) if i not in S and i > t and int(pa[i].get('G_calls', 0)) > 0]
            removed += lam * m.get(t, 0) * len(later)
        dev = round(100 * (B_meas - (b_pred - removed)) / A_tot, 4)
        out['grids'][g] = {'A_measured': A_tot, 'B_measured': B_meas, 'S': S, 'rho_used': rho,
                           'B_pred_raw': round(b_pred, 1), 'removed_mass': round(removed, 1),
                           'B_pred_final': round(b_pred - removed, 1),
                           'drop_meas_pct': round(100 * (1 - B_meas / A_tot), 2),
                           'drop_pred_pct': round(100 * (1 - (b_pred - removed) / A_tot), 2),
                           'dev_pt': round(abs(100 * (1 - B_meas / A_tot) - 100 * (1 - (b_pred - removed) / A_tot)), 3),
                           'dev_rel_pct': abs(dev),
                           'per_turn': resid_rows,
                           'verdict': 'OK' if abs(dev) <= 1.5 else 'WARN'}
    subs = [v for v in out['grids'].values() if isinstance(v, dict)]
    out['verdicts'] = {'MODEL': 'OK' if subs and all(v['verdict'] == 'OK' for v in subs) else ('NO_DATA' if not subs else 'WARN')}
    json.dump(out, open(D / 'model-check-r441.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    for g, v in out['grids'].items():
        print(f'[{g}]', json.dumps({k: v[k] for k in ('A_measured', 'B_measured', 'S', 'B_pred_final', 'drop_meas_pct', 'drop_pred_pct', 'dev_pt', 'verdict')}, ensure_ascii=False)
              if isinstance(v, dict) else v)
    print('[MODEL]', out['verdicts']['MODEL'], '| wrote', D / 'model-check-r441.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
