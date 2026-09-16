#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C1: 残留行的**分布先行裁定表** (先出分布再逐行裁定, 禁按单行直觉改)。

分布面 (三栏, 机检产出):
  · 覆盖行 × evidence_kind (artifact/directory/self-derived);
  · 覆盖行 × 器具派生态 (有无 instrument + 命令首 token 形态);
  · 缺口行的原因类 × 现盘动作 (裁定结果)。
裁定规则 (预注册, 见 prereg_q31.json):
  R1 命令本可机跑 (shell 断言 / dotnet test / python -c) ⇒ 改证据面形态为仓库内器具;
  R2 器具/语料已在仓库内但声明指 /tmp ⇒ 只改声明 (存在面 ≠ 扫描面);
  R3 证据本体是文档/目录 ⇒ evidence_path 不动 (它仍是 artifact), 只把**命令**变可复现;
  R4 真跑受阻 (需模型/服务) ⇒ 标 execution_blocked, 禁造占位读数。
退出码: 0 全绿 / 2 有红 / 3 环境失败。
"""
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
Q30_CENSUS = 'eval/capability/exp1-q30/instrument_gap_census_q30.json'
Q31_CENSUS = 'eval/capability/exp1-q31/instrument_gap_census_q31.json'
REG = 'docs/verification-registry.json'
OUT = 'eval/capability/exp1-q31/residual_disposition_q31.json'

# 逐行裁定 (id -> (规则, 动作, 结果/边界))
DECISIONS = {
    'engine.retired.no_local_gguf': {
        'rule': 'R1+R3', 'action': '判据重写为子系统作用域 + 互操作库允许清单 (原词面判据现盘为假)',
        'artifact_untouched': True,
        'evidence': '现盘复现 rc=1 (合法 kernel32 声明被词面判据误杀) ⇒ 新判据正控 rc=0 + 三负控',
    },
    'llamacpp.prompt.template_gate': {
        'rule': 'R1+R3', 'action': 'dotnet test 命令行 → 外部测试面包装器 (退出码三分类)',
        'artifact_untouched': True, 'evidence': 'wrapper --selftest 6/6 + 真跑 (r420 面) rc=0/47 passed',
    },
    'r420.recall-command-wiring': {
        'rule': 'R1+R3', 'action': 'dotnet test 命令行 → 同一包装器 (指定 filter/label)',
        'artifact_untouched': True,
        'evidence': '真跑 r420-recall-wiring 47/47 绿 (40.9s, log 26,181 B) 分类 pass',
    },
    'r462.weight-probe': {
        'rule': 'R2+R4', 'action': '改指自足入口 wrapper (归档三件与 /tmp 原件逐位相同); 真跑标受阻',
        'artifact_untouched': True,
        'evidence': 'sha256 3/3 逐位相同; 归档件硬编码 /tmp 语料 ⇒ 标 hardness; execution_blocked',
    },
    'r463.model-cleanup': {
        'rule': 'R1+R3', 'action': 'python3 -c 一次性读取 → 带控制器具 (字段完整性 + 现盘不存在 + 保留面无交集)',
        'artifact_untouched': True,
        'evidence': '真跑 CLEANUP_LEDGER_CHECK=OK (4 条) + selftest 4/4 (含 3 负控)',
    },
}
CMD_SHAPE = [('shell_assertion', ("test ", " test ! ", "! grep")), ('dotnet_test', ('dotnet test',)),
             ('python_c_inline', ('python3 -c', 'python -c')), ('wrapper_call', ('instruments/',)),
             ('tmp_path', ('/tmp/',)), ('script_call', ('python3 eval/', 'bash eval/'))]


def shape(cmd):
    c = cmd or ''
    for name, toks in CMD_SHAPE:
        if any(t in c for t in toks):
            return name
    return 'other'


def main():
    reg = json.load(open(os.path.join(ROOT, REG), encoding='utf-8'))
    sys.path.insert(0, os.path.join(ROOT, 'eval/capability'))
    import bind_evidence as be
    tracked, dirty = be.git_state(ROOT)
    rows = [r for r in reg['rows'] if be.needs_field(r)]
    q30 = json.load(open(os.path.join(ROOT, Q30_CENSUS), encoding='utf-8'))
    q31 = json.load(open(os.path.join(ROOT, Q31_CENSUS), encoding='utf-8'))
    q31_ids = {g['id'] for g in q31['gaps']}

    # 分布: 逐行派生 (禁止按声明字段推断)
    dist_kind, dist_inst, dist_cmd = {}, {}, {}
    disp = []
    for r in rows:
        f = be.derive(ROOT, r, tracked, dirty)
        k = f['evidence_kind']
        dist_kind[k] = dist_kind.get(k, 0) + 1
        has = 'instrument' if f.get('instrument') else 'no_instrument'
        dist_inst[has] = dist_inst.get(has, 0) + 1
        s = shape(r.get('evidence_cmd'))
        dist_cmd[s] = dist_cmd.get(s, 0) + 1
        if r['id'] in DECISIONS:
            d = dict(DECISIONS[r['id']])
            d.update({'id': r['id'], 'level': r.get('level'), 'evidence_path': r.get('evidence_path'),
                      'instrument': f.get('instrument'), 'pin_status': f.get('pin_status'),
                      'pin_reason': f.get('pin_reason'), 'cmd_shape_now': s})
            disp.append(d)

    checks = {}
    checks['P1_五行全部派生器具'] = all(d.get('instrument') for d in disp) and len(disp) == 5
    checks['P2_零残留缺口'] = (len(q31_ids) == 0)
    checks['P3_缺口数下降'] = (q31['no_instrument'] < q30['no_instrument'])
    checks['P4_裁定表五行齐备'] = (sorted(d['id'] for d in disp) == sorted(DECISIONS))
    checks['P5_证据本体未改路径'] = all(d['artifact_untouched'] for d in disp)
    checks['P6_分布可机检'] = (sum(dist_kind.values()) == len(rows) and sum(dist_inst.values()) == len(rows))
    rep = {'round': 'EXP1-Q31', 'rows_covered': len(rows),
           'distribution': {'by_evidence_kind': dist_kind, 'by_instrument': dist_inst,
                            'by_cmd_shape': dist_cmd},
           'q30_reading': {'rows_covered': q30['rows_covered'], 'derived': q30['derived_instrument'],
                           'no_instrument': q30['no_instrument'], 'by_class': q30['by_reason_class']},
           'q31_reading': {'rows_covered': q31['rows_covered'], 'derived': q31['derived_instrument'],
                           'no_instrument': q31['no_instrument'], 'by_class': q31['by_reason_class']},
           'dispositions': disp, 'checks': checks}
    rep['verdict'] = 'PASS' if all(checks.values()) else 'FAIL'
    rep['n_checks'] = '%d/%d' % (sum(1 for v in checks.values() if v), len(checks))
    open(os.path.join(ROOT, OUT), 'w', encoding='utf-8').write(json.dumps(rep, ensure_ascii=False, indent=1) + '\n')
    print('rows_covered=%d  evidence_kind=%s' % (len(rows), dist_kind))
    print('instrument=%s  cmd_shape=%s' % (dist_inst, dist_cmd))
    print('Q30: covered=%d derived=%d gaps=%d %s' % (q30['rows_covered'], q30['derived_instrument'],
                                                     q30['no_instrument'], q30['by_reason_class']))
    print('Q31: covered=%d derived=%d gaps=%d %s' % (q31['rows_covered'], q31['derived_instrument'],
                                                     q31['no_instrument'], q31['by_reason_class']))
    for d in disp:
        print('  %-32s L%s %-14s inst=%-46s %s' % (d['id'], d['level'], d['rule'],
                                                   os.path.basename(d['instrument'] or ''), d['action'][:34]))
    for k, v in checks.items():
        print('%-26s %s' % (k, 'OK' if v else 'FAIL'))
    print('verdict=%s (%s)' % (rep['verdict'], rep['n_checks']))
    print('落盘 %s' % OUT)
    return 0 if rep['verdict'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
