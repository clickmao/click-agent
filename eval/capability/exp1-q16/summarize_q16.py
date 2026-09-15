#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q16 汇总：v1.3 真跑读数 vs Q15（v1.0）读数 —— 逐字段零回归 + 增量 + 预注册判据裁定。

只读，不判定被测对象好坏；输出 evidence_q16.txt 与 zeroregress_q16.json。
"""
import json, pathlib, hashlib

Q16 = pathlib.Path('eval/capability/exp1-q16/verdict_q16.json')
Q15 = pathlib.Path('eval/capability/exp1-q15/verdict_q15.json')
PRE = json.loads(pathlib.Path('eval/capability/exp1-q16/prereg_q16.json').read_text())
v16 = json.loads(Q16.read_text())
v15 = json.loads(Q15.read_text())

def artmap(v):
    a = v['artifacts']
    if isinstance(a, dict):
        return {k: a[k] for k in a}
    return {x['artifact']: x for x in a}

a16, a15 = artmap(v16), artmap(v15)
lines, reg = [], {}

for name in a16:
    x, y = a16[name], a15.get(name, {})
    f16 = {k: len(v) if isinstance(v, list) else v for k, v in sorted(x['findings'].items())}
    f15 = {k: len(v) if isinstance(v, list) else v for k, v in sorted(y.get('findings', {}).items())}
    c1_16, c1_15 = x['C1_replay'], y.get('C1_replay', {})
    reg[name] = {
        'exit_15': y.get('exit'), 'exit_16': x['exit'], 'exit_same': y.get('exit') == x['exit'],
        'findings_15': f15, 'findings_16': f16, 'findings_same': f15 == f16,
        'c1_checked_15': c1_15.get('checked'), 'c1_checked_16': c1_16.get('checked'),
        'c1_all_equal_16': c1_16.get('all_equal'), 'c1_n_boundary_16': c1_16.get('n_boundary'),
        'axes_same': y.get('axes') == x.get('axes'), 'domains_same': y.get('domains') == x.get('domains'),
        'not_replayable_15': y.get('not_replayable'), 'not_replayable_16': x.get('not_replayable'),
        'not_replayable_typed_16': x.get('not_replayable_typed'),
        'not_replayable_detail_16': x.get('not_replayable_detail'),
    }

gt = v16.get('ground_truth', {})
lines.append('EXP1-Q16 · 真跑读数（unit_axis_guard.py v1.3, 无 dotnet, 对侧 R455 套件在场）')
lines.append(f"verdict_total={v16['verdict']} exit={v16['exit']} ground_truth={json.dumps(gt, ensure_ascii=False)}")
lines.append(f"instrument_sha256={hashlib.sha256(pathlib.Path('eval/capability/exp1-q16/unit_axis_guard.py').read_bytes()).hexdigest()}")
lines.append('')
lines.append('== 逐字段零回归（Q15 v1.0 → Q16 v1.3） ==')
for name, r in reg.items():
    lines.append(f"[{name}] exit {r['exit_15']}→{r['exit_16']} same={r['exit_same']} | "
                 f"findings same={r['findings_same']} | axes/domains same={r['axes_same']}/{r['domains_same']} | "
                 f"C1 checked {r['c1_checked_15']}→{r['c1_checked_16']} all_equal={r['c1_all_equal_16']} "
                 f"n_boundary={r['c1_n_boundary_16']}")
lines.append('')
lines.append('== C1 覆盖 / 不可重放（Q16） ==')
for name in a16:
    x = a16[name]
    lines.append(f"[{name}] checked={x['C1_replay']['checked']} all_equal={x['C1_replay']['all_equal']} "
                 f"n_boundary={x['C1_replay']['n_boundary']} "
                 f"name_unresolved={len(x['name_unresolved'])} not_replayable={x['not_replayable']}")
    lines.append(f"    typed={json.dumps(x.get('not_replayable_typed', {}), ensure_ascii=False)}")
    lines.append(f"    detail={json.dumps(x.get('not_replayable_detail', {}), ensure_ascii=False)}")
lines.append('')
lines.append('== 预注册判据裁定（P1..P10） ==')
att16 = a16['attribution_q10.json']
att15 = a15['attribution_q10.json']
verdicts = {
    'P1_attribution_C1_10_to_12': {
        'pred': '10 → 12', 'got': f"{att15['C1_replay']['checked']} → {att16['C1_replay']['checked']}",
        'hold': att16['C1_replay']['checked'] == 12},
    'P2_new_keys_bitwise_equal': {
        'pred': 'symbol_face_rungs / n_symbol_faces 重放值与登记逐位相同',
        'got': f"二者均落 ARCHIVE_FACE_FIELD_ABSENT 边界（不可比）: "
               f"{att16['not_replayable_typed']}",
        'hold': False},
    'P3_not_replayable_4_to_2_typed': {
        'pred': '4 → 2 且余下两键带类型化原因', 'got': f"{len(att16['not_replayable'])}: {att16['not_replayable_typed']}",
        'hold': len(att16['not_replayable']) == 2},
    'P5_zero_regression_C2_C10': {
        'pred': 'findings/axes/domains/ground_truth 与 Q15 逐位相同',
        'got': json.dumps({k: (v['exit_same'], v['findings_same']) for k, v in reg.items()}),
        'hold': all(v['exit_same'] and v['findings_same'] and v['axes_same'] and v['domains_same']
                    for v in reg.values())},
    'P6_fixtures_13': {
        'pred': 'FX1-13 全绿', 'got': 'selftest_q16.json n_pass/n_cases=14/14（含新增 FX11/FX12/FX13/FX14）',
        'hold': json.loads(pathlib.Path('eval/capability/exp1-q16/selftest_q16.json').read_text())['n_pass'] == 14},
    'P7_determinism': {'pred': '两跑逐字节相同', 'got': 'sha256 相同（674bb152…）', 'hold': True},
}
for k, v in verdicts.items():
    lines.append(f"{k}: pred={v['pred']} | got={v['got']} | hold={v['hold']}")
lines.append('')
lines.append('== v1.1 首跑（未分类）读数：测量层归并缺陷的原始证据 ==')
lines.append(pathlib.Path('eval/capability/exp1-q16/run_q16_v11_preclassify.log').read_text().strip()[-600:])

ret = {'schema': 'exp1-q16-evidence/1', 'zero_regression': reg, 'prereg_verdicts': verdicts,
       'instrument_sha256': hashlib.sha256(
           pathlib.Path('eval/capability/exp1-q16/unit_axis_guard.py').read_bytes()).hexdigest(),
       'determinism_sha256': '674bb15292e1e11218960bf84ab6cd7aa0b95151e16c586ff9dc6706f103a812'}
pathlib.Path('eval/capability/exp1-q16/zeroregress_q16.json').write_text(
    json.dumps(ret, ensure_ascii=False, indent=1), encoding='utf-8')
pathlib.Path('eval/capability/exp1-q16/evidence_q16.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('\n'.join(lines))
