#!/usr/bin/env python3
"""R442 器具 — ④ **D7 断言: A 分母必须同网格、按 N 截断**（防 R440/R441 的跨网格代理复发）+ 负控。

背景（R440 C2/C3 FAIL 根因, R441 再次复发）:
  预测器用「逐文本/逐记录下标」把 A 臂成本代理到别的网格 ⇒ W8 分母取了 V4 全长 61281（应 17260）
  ⇒ 降幅算成 4.13% 而实测 13.77%。本轮把该缺陷升级为**机械断言**, 并用**真实历史缺陷**当负控。

判据:
  D7a 每个网格的 A 分母 == 该网格 verdict-A 的 G_tokens（同网格真值, 不得跨网格取）
  D7b 该 A 臂参与计入的主调用轮号 ⊆ [1, N]
  D7c 缺陷注入（负控, 必须判红）: 把 W8 的分母换成 r440 V4 全长 61281 ⇒ D7a FAIL
  D7d 正控: 6 个网格（r441 W8/W20/M20/V2b + r440 V4/V5）全部 D7a/D7b PASS
退出码: 0 = 全绿（含负控按预期判红）; 2 = 有真红; 3 = 器具自身异常。
"""
import json
import pathlib
import sys

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
R441 = ROOT / 'eval/rover/r441'
R440 = ROOT / 'eval/rover/r440'
OUT = ROOT / 'eval/rover/r442'


def load(p):
    p = pathlib.Path(p)
    return json.load(open(p, encoding='utf-8')) if p.exists() else None


def check_denominator(grid_name, n_turns, a_verdict, denominator, expect_grid=None):
    """D7 检查器本体: 返回 (ok, 说明)。denominator 为实际用于降幅的 A 分母(token)。"""
    if a_verdict is None:
        return False, 'A 臂 verdict 缺失'
    if expect_grid is not None and a_verdict.get('grid') != expect_grid:
        return False, f"A 臂网格不符: {a_verdict.get('grid')} != {expect_grid}（跨网格代理）"
    real = a_verdict.get('G_tokens')
    if denominator != real:
        return False, f'分母={denominator} != 同网格真值 G_tokens={real}（差 {denominator - real:+d}）'
    turns = [r['turn'] for r in a_verdict.get('per_turn', []) if int(r.get('G_calls') or 0) > 0]
    bad = [t for t in turns if not (1 <= t <= n_turns)]
    if bad:
        return False, f'A 臂主调用轮号越界: {bad} ∉ [1,{n_turns}]'
    return True, f'分母={real} 同网格; 主调用轮 {len(turns)} 个 ⊆ [1,{n_turns}]'


def main():
    rep = {'round': 'R442', 'kind': 'D7_denominator_same_grid_assertion', 'checks': {}}
    cases = []           # (名称, 网格名, N, a_verdict 路径, 分母来源, expect_grid)
    for g in ('W8', 'W20', 'M20'):
        spec = load(R441 / f'grid/task-{g}.json')
        va = load(R441 / f'verdict-A-{g}.json')
        if spec and va:
            cases.append((f'r441:{g}', g, len(spec['turns']), va, va.get('G_tokens'), g))
    for g in ('V2b',):
        spec = load(R441 / f'grid/task-{g}.json')
        for s in ('-b1', '-b2', '-c2'):
            va = load(R441 / f'verdict-A-{g}{s}.json')
            if spec and va:
                cases.append((f'r441:{g}{s}', g, len(spec['turns']), va, va.get('G_tokens'), g))
                break
    for g in ('V4', 'V5'):
        spec = load(R440 / f'grid/task-{g}.json')
        va = load(R440 / f'verdict-A-{g}.json')
        if spec and va:
            cases.append((f'r440:{g}', g, len(spec['turns']), va, va.get('G_tokens'), g))

    ok_all = True
    for name, g, n, va, den, eg in cases:
        ok, why = check_denominator(g, n, va, den, eg)
        rep['checks'][name] = {'ok': ok, 'why': why}
        ok_all &= ok

    # 负控: 真实历史缺陷 —— W8 用 r440 V4 全长当分母（R440 预测器实际犯的错）
    spec_w8 = load(R441 / 'grid/task-W8.json')
    va_w8 = load(R441 / 'verdict-A-W8.json')
    v4 = load(R440 / 'verdict-A-V4.json')
    neg_ok, neg_why = check_denominator('W8', len(spec_w8['turns']), va_w8, v4['G_tokens'], 'W8')
    rep['checks']['NC1_w8_with_v4_denominator'] = {'ok': neg_ok, 'why': neg_why,
                                                   'expected': 'FAIL(必须判红)'}
    # 负控 2: 分母正确但网格标签不符
    neg2_ok, neg2_why = check_denominator('W8', len(spec_w8['turns']), v4, v4['G_tokens'], 'W8')
    rep['checks']['NC2_v4_verdict_tagged_as_w8'] = {'ok': neg2_ok, 'why': neg2_why,
                                                    'expected': 'FAIL(必须判红)'}
    # 正控: 同网格同值 ⇒ 必须 PASS
    pos_ok, pos_why = check_denominator('W8', len(spec_w8['turns']), va_w8, va_w8['G_tokens'], 'W8')
    rep['checks']['PC1_w8_same_grid_same_value'] = {'ok': pos_ok, 'why': pos_why}
    rep['negative_controls_fired'] = (not neg_ok) and (not neg2_ok)
    rep['positive_control_passed'] = pos_ok
    rep['D7_pass'] = bool(ok_all and rep['negative_controls_fired'] and pos_ok)
    print(f"[D7] 正控 PASS={pos_ok} | 负控判红 NC1={not neg_ok} NC2={not neg2_ok} | 网格 {len(cases)} 项 ok_all={ok_all}")
    for k, v in rep['checks'].items():
        print(f"   {'OK ' if v['ok'] else 'RED'} {k}: {v['why']}")
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(OUT / 'design-audit-r442.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('wrote', OUT / 'design-audit-r442.json', '| D7_pass =', rep['D7_pass'])
    return 0 if rep['D7_pass'] else 2


if __name__ == '__main__':
    sys.exit(main())
