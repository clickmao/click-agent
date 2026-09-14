#!/usr/bin/env python3
"""R441 预注册预测器 — 两参数律（δ 逐轮常数 + m 位置曲线）在**新网格**上的外推。

与 R440 的差别（本轮升级点, 用户令「②」）:
  * A 分母一律取**同网格实测**或**前缀恒等代理**（R440 部分用跨网格代理 ⇒ 事后被判为失准源）
  * δ 与 m **程序化派生**自存档 verdict/calls（禁手打数字）: δ = 非跳单调用轮 B(i)-A(i) 的中位
  * 新增 ρ = 被跳轮的**残余远端成本**（实测 R440 构建: 微步骤隔离问询 34+7=41 tok; R439/R438 构建实测 0）
    ⇒ 预测以**区间**给出（ρ=41 主分支 / ρ=0 次分支）, 不确定度 < 0.7pt
  * 模型: B(i) = A(i) + δ − Σ_{t∈S, t<i} m(t)   (i ∉ S)   ;   B(t) = ρ   (t ∈ S)
  输出 eval/rover/r441/predict-r441-pre.json（跑测前落盘 ⇒ 预注册）。
"""
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
R = {k: ROOT / f'eval/rover/{k}' for k in ('r436', 'r438', 'r439', 'r440', 'r441')}
MARK = '[本轮参考上下文]'

ARCH = [
    (R['r440'], 'V1', 'verdict-A-V1.json', 'verdict-BRJ-V1.json', 'calls-A-V1.jsonl', 'calls-BRJ-V1.jsonl'),
    (R['r440'], 'V2b', 'verdict-A-V2b-b1.json', 'verdict-BRJ-V2b-b1.json', 'calls-A-V2b-b1.jsonl', 'calls-BRJ-V2b-b1.jsonl'),
    (R['r440'], 'V4', 'verdict-A-V4.json', 'verdict-BRJ-V4.json', 'calls-A-V4.jsonl', 'calls-BRJ-V4.jsonl'),
    (R['r440'], 'V5', 'verdict-A-V5.json', 'verdict-BRJ-V5.json', 'calls-A-V5.jsonl', 'calls-BRJ-V5.jsonl'),
    (R['r439'], 'V20', 'verdict-A-V20.json', 'verdict-BRJ-V20.json', 'calls-A-V20.jsonl', 'calls-BRJ-V20.jsonl'),
    (R['r439'], 'p8', 'verdict-A-p8.json', 'verdict-BRJ-p8.json', 'calls-A-p8.jsonl', 'calls-BRJ-p8.jsonl'),
    (R['r438'], 'p12', 'verdict-A-p12.json', 'verdict-BRJ-p12.json', 'calls-A-p12.jsonl', 'calls-BRJ-p12.jsonl'),
]


def load(p):
    return json.load(open(p, encoding='utf-8')) if pathlib.Path(p).exists() else None


def blocks_by_turn(calls_path, grid_turns):
    """每轮内联块质量（token = chars//2）: 从 calls 中带 MARK 的 user 消息反推; 轮号按前缀文本**精确**匹配。"""
    tm = {(t or '').strip(): i + 1 for i, t in enumerate(grid_turns)}
    out = {}
    for rec in (load_jsonl(calls_path)):
        for m in rec.get('messages') or []:
            if m.get('role') != 'user':
                continue
            c = str(m.get('content') or '')
            i = c.find(MARK)
            if i < 0:
                continue
            t = tm.get(c[:i].strip())
            if not t:
                continue
            out.setdefault(t, []).append(len(c[i:]) // 2)
    return {k: int(statistics.median(v)) for k, v in out.items()}


def load_jsonl(p):
    p = pathlib.Path(p)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def main():
    verdicts, grids, m_pos = {}, {}, {}
    for base, g, fa, fb, ca, cb in ARCH:
        v_a, v_b = load(base / fa), load(base / fb)
        if v_a:
            verdicts[(g, 'A')] = v_a
        if v_b:
            verdicts[(g, 'BRJ')] = v_b
        if g not in grids:
            for d in (R['r441'] / 'grid', R['r440'] / 'grid', R['r439'] / 'grid', R['r436'] / 'grid', R['r438'] / 'grid'):
                p = d / f'task-{g}.json'
                if p.exists():
                    grids[g] = json.load(open(p, encoding='utf-8'))
                    break
        if g in grids:
            for tag, fn in (('A', ca), ('BRJ', cb)):
                for t, v in blocks_by_turn(base / fn, grids[g]['turns']).items():
                    m_pos.setdefault(t, []).append(v)
    for d in (R['r441'] / 'grid',):
        for p in sorted(d.glob('task-*.json')):
            grids.setdefault(p.stem.replace('task-', ''), json.load(open(p, encoding='utf-8')))
    m_obs = {t: int(statistics.median(v)) for t, v in sorted(m_pos.items())}

    # ---- ① δ: 仅取**两臂同为单调用且治疗臂为 pass** 的轮（其余轮含多调用/消化轮, 会污染） ----
    per_turn = {k: {r['turn']: r for r in v.get('per_turn', [])} for k, v in verdicts.items()}
    d_rows, rho_obs = [], []
    for base, g, *_ in ARCH:
        pa, pb = per_turn.get((g, 'A')), per_turn.get((g, 'BRJ'))
        if not pa or not pb:
            continue
        for t in sorted(set(pa) & set(pb)):
            ra, rb = pa[t], pb[t]
            if rb.get('actual') == 'skip':
                rho_obs.append({'grid': g, 'turn': t, 'tok': int(rb.get('G_tokens', 0))})
            elif (int(ra.get('G_calls', 0)) == 1 and int(rb.get('G_calls', 0)) == 1
                  and int(ra.get('G_tokens', 0)) > 0 and int(rb.get('G_tokens', 0)) > 0):
                d_rows.append({'grid': g, 'turn': t, 'delta': int(rb['G_tokens']) - int(ra['G_tokens'])})
    d_vals = [r['delta'] for r in d_rows]
    delta = int(statistics.median(d_vals)) if d_vals else 0
    d_spread = {'n': len(d_vals), 'min': min(d_vals), 'max': max(d_vals), 'all_equal': len(set(d_vals)) == 1,
                'per_grid': {g: sorted({r['delta'] for r in d_rows if r['grid'] == g}) for g, _ in {(r['grid'], 0) for r in d_rows}},
                'rows': d_rows}
    rho_vals = [r['tok'] for r in rho_obs]
    rho_groups = {}
    for r in rho_obs:
        rho_groups.setdefault(r['grid'], []).append(r['tok'])
    rho = {'obs': rho_obs, 'by_grid': {k: sorted(set(v)) for k, v in rho_groups.items()},
           'primary': 41 if 41 in rho_vals else (max(rho_vals) if rho_vals else 0),
           'branch_zero': 0}

    def m_of(t):
        if t in m_obs:
            return m_obs[t]
        ks = sorted(m_obs)
        if not ks:
            return 0
        lo = [k for k in ks if k < t]
        hi = [k for k in ks if k > t]
        if lo and hi:
            a, b = max(lo), min(hi)
            return int(m_obs[a] + (m_obs[b] - m_obs[a]) * (t - a) / (b - a))
        if not hi:
            a, b = ks[-2], ks[-1]
            return int(m_obs[b] + (m_obs[b] - m_obs[a]) * (t - b) / (b - a))
        return m_obs[ks[0]]

    def model(grid, S, A_map, rho_val, lam=1.0):
        S = set(S)
        tot_a = sum(A_map.values())
        b, removed, n_pass = 0.0, 0.0, 0
        for i, a in A_map.items():
            if i in S:
                b += rho_val
                continue
            b += a + delta
            n_pass += 1
            for t in S:
                if t < i:
                    removed += m_of(t)
        removed *= lam
        return {'A_total': tot_a, 'B_pred': round(b - removed), 'removed_mass': round(removed),
                'n_pass_calls': n_pass, 'n_skip': len(S),
                'drop_pct': round(100 * (1 - (b - removed) / tot_a), 2) if tot_a else None}

    def a_map(g):
        pt = per_turn.get((g, 'A')) or {}
        return {t: int(r.get('G_tokens', 0)) for t, r in pt.items()}

    def a_map_proxy(proxy_g, tgt_grid):
        am, pt, pg = a_map(proxy_g), grids[tgt_grid]['turns'], grids[proxy_g]['turns']
        out = {}
        for t, v in am.items():
            if t <= len(pt):
                out[t] = v + (len(pt[t - 1].strip()) - len(pg[t - 1].strip())) // 2
            # 【R441 事后修复 D1】t > N 的代理轮必须**丢弃**（预注册版误留 ⇒ W8 分母 = V4 全长 61281, 应为 17260 ⇒ C3-W8 判红）
        return out

    # ---- λ 标定: 弃块质量 m(t) 来自**字符长度中位**, 与真实 token 节省存在系统偏差 ⇒ 在带移除项的存档网格上拟合单一比例
    lam_grids = []
    for base, g, *_ in ARCH:
        pv, pa = verdicts.get((g, 'BRJ')), verdicts.get((g, 'A'))
        if not pv or not pa:
            continue
        S = sorted(r['turn'] for r in pv['per_turn'] if r.get('actual') == 'skip')
        if not S:
            continue
        A_map = a_map(g)
        meas = int(pv.get('tokens_total') or sum(r.get('G_tokens', 0) for r in pv['per_turn']))
        base_no = model(g, S, A_map, rho_val=0, lam=0.0)['B_pred']
        mass = model(g, S, A_map, rho_val=0, lam=1.0)['removed_mass']
        if mass > 0:
            lam_grids.append({'grid': g, 'removed_mass': mass, 'meas': meas, 'model_no_removed': base_no,
                              'lam_opt': round((base_no - meas) / mass, 4)})
    lam = float(statistics.median([r['lam_opt'] for r in lam_grids])) if lam_grids else 1.0
    lam = max(0.0, min(1.2, lam))
    lam_report = {'lam': round(lam, 4), 'fitted_on': lam_grids}

    # ---- ② 样本内自校验（存档网格; 主模型 = λ 标定后） ----
    in_sample = {}
    for g, _ in [(a[1], a[0]) for a in ARCH]:
        pv, pa = verdicts.get((g, 'BRJ')), verdicts.get((g, 'A'))
        if not pv or not pa:
            continue
        S = sorted(r['turn'] for r in pv['per_turn'] if r.get('actual') == 'skip')
        A_map = a_map(g)
        m1 = model(g, S, A_map, rho_val=0, lam=lam)
        m2 = model(g, S, A_map, rho_val=0, lam=0.0)
        meas = int(pv.get('tokens_total') or sum(r.get('G_tokens', 0) for r in pv['per_turn']))
        meas_a = int(pa.get('tokens_total') or sum(r.get('G_tokens', 0) for r in pa['per_turn']))
        in_sample[g] = {'S': S, 'measured_A': meas_a, 'measured_BRJ': meas,
                        'model_with_removed': m1['B_pred'], 'dev_removed_pct': round(100 * abs(m1['B_pred'] - meas) / meas, 3),
                        'model_no_removed': m2['B_pred'], 'dev_no_removed_pct': round(100 * abs(m2['B_pred'] - meas) / meas, 3),
                        'removed_mass': m1['removed_mass'],
                        'drop_meas_pct': round(100 * (1 - meas / meas_a), 2) if meas_a else None}
    devs = [v['dev_removed_pct'] for v in in_sample.values()]
    in_sample_verdict = ('OK(<=3%)' if devs and max(devs) <= 3.0 else
                         ('WARN(>3%, 已在报告中降级为区间预测)' if devs else 'NO_DATA'))

    # ---- ③ 新网格预注册预测（主分支 ρ=41, 次分支 ρ=0） ----
    preds = {}
    for g, S, proxy in (('W8', [8], 'V4'), ('W20', [20], 'V4'), ('M20', [7, 8, 9, 10, 11, 12, 13], 'V4'), ('V2b', [4], None)):
        A_map = a_map(g) if proxy is None else a_map_proxy(proxy, g)
        m_main = model(g, S, A_map, rho_val=rho['primary'], lam=lam)
        m_zero = model(g, S, A_map, rho_val=0, lam=lam)
        m_norm = model(g, S, A_map, rho_val=rho['primary'], lam=0.0)
        preds[g] = {'S': S, 'A_source': '同网格实测 A' if proxy is None else f'代理 A({proxy}), 前缀恒等轮={grids[g]["prefix_identity_turns"]}',
                    'A_total': m_main['A_total'], 'n_skip': len(S),
                    'B_pred_main': m_main['B_pred'], 'drop_main_pct': m_main['drop_pct'],
                    'B_pred_rho0': m_zero['B_pred'], 'drop_rho0_pct': m_zero['drop_pct'],
                    'B_pred_no_removed': m_norm['B_pred'], 'drop_no_removed_pct': m_norm['drop_pct'],
                    'removed_mass': m_main['removed_mass'],
                    'drop_bracket_pct': [min(m_zero['drop_pct'], m_norm['drop_pct'], m_main['drop_pct']),
                                         max(m_zero['drop_pct'], m_norm['drop_pct'], m_main['drop_pct'])]}
    out = {'round': 'r441', 'pre_registered_utc': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
           'model': {'delta_per_turn': delta, 'delta_spread': d_spread, 'rho_skip_residual': rho,
                     'lambda_removal_calibration': lam_report, 'block_mass_medians': m_obs},
           'in_sample_validation': in_sample, 'in_sample_verdict': in_sample_verdict,
           'predictions': preds}
    _out = __import__('os').environ.get('R441_OUT', 'predict-r441-pre.json')
    if _out != 'predict-r441-pre.json':
        out['POST_HOC'] = True
        out['supersedes'] = 'predict-r441-pre.json（预注册件; 缺陷: a_map_proxy 未按 N 截断 ⇒ W8 分母错误）'
    json.dump(out, open(R['r441'] / _out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('[δ] value =', delta, 'n =', d_spread['n'], 'range', d_spread['min'], d_spread['max'], 'all_equal =', d_spread['all_equal'])
    print('[δ] per_grid =', d_spread['per_grid'])
    print('[ρ] by_grid =', rho['by_grid'], 'primary =', rho['primary'])
    print('[λ] =', lam_report['lam'], 'fitted_on =', lam_report['fitted_on'])
    print('[m] =', m_obs)
    for g, v in in_sample.items():
        print(f'[in-sample] {g}: S={v["S"]} A={v["measured_A"]} B_meas={v["measured_BRJ"]} drop_meas={v["drop_meas_pct"]}% '
              f'| model(removed)={v["model_with_removed"]} dev={v["dev_removed_pct"]}% | model(no-removed)={v["model_no_removed"]} dev={v["dev_no_removed_pct"]}%')
    print('[in-sample verdict]', in_sample_verdict)
    for g, v in preds.items():
        print(f'[PRED] {g}: S={v["S"]} A={v["A_total"]} drop_main={v["drop_main_pct"]}% (ρ=0: {v["drop_rho0_pct"]}%, 无移除项: {v["drop_no_removed_pct"]}%) '
              f'bracket={v["drop_bracket_pct"]} removed={v["removed_mass"]} | {v["A_source"]}')
    print('[wrote]', R['r441'] / _out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
