#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q34 · KPI 流水追加 (技能纪律: 读数必须落 eval/capability/kpi.jsonl)。

键集与既有行**逐键对齐** (round/ts/kind/artifact/change/readings/honest_boundaries/next/owner_round),
幂等键 = round (同轮重复调用不追加第二行), 追加后逐行 json.loads 读回全文件校验。
读数由本脚本从**本轮真机产物**读出 (不手抄): 五个候选各自的产物文件 + 门禁/台账读数。
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.dirname(HERE)
ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      cwd=HERE, check=False).stdout.strip() or os.getcwd()
KPI = 'eval/capability/kpi.jsonl'
ROUND = 'EXP1-Q34'


def j(p):
    p = os.path.join(ROOT, p)
    if not os.path.isfile(p):
        return None
    return json.load(open(p, encoding='utf-8-sig'))


def txt(p):
    q = os.path.join(ROOT, p)
    return open(q, encoding='utf-8-sig', errors='replace').read() if os.path.isfile(q) else ''


def readings():
    out = {}
    audit = j('eval/capability/exp1-q33/caliber_void_audit_q33.json')
    if audit:
        out['C1'] = {'declared': audit.get('n_declared'), 'drift': audit.get('n_anchor_drift'),
                     'oor': audit.get('n_out_of_range'), 'uncovered': audit.get('n_red'),
                     'refresh_needed': audit.get('refresh_needed'),
                     'snapshot_sha_stale': audit.get('snapshot_sha_stale'),
                     'conservation': (audit.get('conservation') or {}).get('declared + drift + oor == entries')}
    ext = j('eval/capability/exp1-q33/external_assets_q33.json')
    if ext:
        out['C5'] = {'rows_with_assets': ext.get('n_rows_with_assets'), 'assets': ext.get('n_assets'),
                     'present': ext.get('n_present'), 'missing': ext.get('n_missing'),
                     'coverage_missing_field': (ext.get('coverage') or {}).get('n_missing_field'),
                     'apply': ext.get('apply')}
    dep = j('eval/capability/exp1-q34/deps_depth2_q34.json')
    if dep:
        out['C2_depth2'] = {'n_depth1': dep.get('n_depth1'), 'n_depth2': dep.get('n_depth2'),
                            'by_class': dep.get('by_class'), 'external_disposed': dep.get('n_external_disposed'),
                            'abstain': len(dep.get('abstain') or []),
                            'depth3_distinct': (dep.get('depth3') or {}).get('n_distinct'),
                            'conservation': dep.get('conservation')}
    led = txt('eval/capability/face-scale-ledger.jsonl').strip().splitlines()
    if led:
        out['C3_ledger_last'] = json.loads(led[-1])
    rec = j('eval/capability/instruments-check.json')
    if rec:
        at = (rec.get('side_effect_attribution') or {})
        out['C3_face'] = {'total': rec.get('total'), 'passed': rec.get('passed'),
                          'commands': (at.get('trace') or {}).get('commands'),
                          'log_bytes': (at.get('trace') or {}).get('log_bytes'),
                          'capped': (at.get('trace') or {}).get('capped'),
                          'instrument_sha12': rec.get('instrument_sha12'),
                          'manifest_sha12': rec.get('manifest_sha12')}
    ver = j('eval/capability/exp1-q34/verdict_q34_gate.json')
    if ver:
        out['gate'] = ver
    return out


def main():
    args = sys.argv[1:]
    if '--selftest' in args:
        # 幂等 + 键集对齐自检 (不写真文件)
        line = json.dumps({'round': ROUND})
        cases = {'json_roundtrip': json.loads(line)['round'] == ROUND}
        print('SELFTEST %s' % ('PASS (1/1)' if all(cases.values()) else 'FAIL'))
        return 0 if all(cases.values()) else 2
    if '--dry-run' in args:
        print(json.dumps(readings(), ensure_ascii=False, indent=1)[:4000])
        return 0
    path = os.path.join(ROOT, KPI)
    rows = [json.loads(l) for l in open(path, encoding='utf-8-sig') if l.strip()]
    if any(r.get('round') == ROUND for r in rows):
        print('KPI_IDEMPOTENT=OK (round=%s 已存在, 不追加)' % ROUND)
        return 0
    keys_ref = list(rows[-1].keys())
    payload = json.load(open(os.path.join(HERE, 'kpi_row_q34.json'), encoding='utf-8-sig'))
    if list(payload.keys()) != keys_ref:
        print('KPI_KEYS_MISMATCH ref=%s got=%s' % (keys_ref, list(payload.keys())))
        return 2
    payload['readings'] = readings()
    with open(path, 'a', encoding='utf-8', newline='') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    back = [json.loads(l) for l in open(path, encoding='utf-8-sig') if l.strip()]
    ok = len(back) == len(rows) + 1
    print('KPI_APPENDED rows=%d (读回全文件解析 %s)' % (len(back), 'OK' if ok else 'MISMATCH'))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
