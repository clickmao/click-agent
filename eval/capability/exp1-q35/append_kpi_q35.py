#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q35 · KPI 流水追加 (技能纪律: 读数必须落 eval/capability/kpi.jsonl)。

键集与既有行**逐键对齐** (round/ts/kind/artifact/change/readings/honest_boundaries/next/owner_round);
幂等键 = round (同轮重复调用不追加第二行); 追加后逐行 json.loads 读回校验。
读数一律从**本轮真机产物**读出 (不手抄): 面差分 / license 审计 / depth-3 / 门禁读数。
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.dirname(HERE)
ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      cwd=HERE, check=False).stdout.strip() or os.getcwd()
KPI = 'eval/capability/kpi.jsonl'
ROUND = 'EXP1-Q35'


def j(p):
    q = os.path.join(ROOT, p)
    if not os.path.isfile(q):
        return None
    return json.load(open(q, encoding='utf-8-sig'))


def main():
    delta = j('eval/capability/exp1-q35/face_delta_q35.json') or {}
    lic = j('eval/capability/exp1-q35/license_audit_q35.json') or {}
    d3 = j('eval/capability/exp1-q35/depth3_recursion_q35.json') or {}
    gate = j('eval/capability/exp1-q35/verdict_q35_gate.json') or {}
    face = j('eval/capability/instruments-check.json') or {}
    rows = []
    for p in (delta.get('pairs') or []):
        rows.append({'pair': p['pair'], 'same_state': p['same_tree_state'],
                     'leaves': p['n_differing_leaves'], 'unattributed': p['n_unattributed'],
                     'digest_a': p.get('digest_a'), 'digest_b': p.get('digest_b')})
    readings = {
        'D1_face_delta': {'digests': {r['path'].split('/')[-1]: r['proj_digest']
                                      for r in (delta.get('records') or [])},
                          'pairs': rows, 'verdict': delta.get('verdict'),
                          'behaviour_stable_same_state': delta.get('behaviour_stable_same_state')},
        'D2_pin_derivation': gate.get('pin_derivation'),
        'D3_license': {'n_items': (lic.get('conservation') or {}).get('n_items'),
                       'states': (lic.get('conservation') or {}).get('states'),
                       'histogram': lic.get('license_id_histogram'),
                       'grades': lic.get('evidence_grade_histogram'),
                       'distinct_packages': lic.get('distinct_packages_resolved'),
                       'bytes_drift_rows': (lic.get('conservation') or {}).get('bytes_drift_rows'),
                       'nested_pairs': (lic.get('conservation') or {}).get('nested_pairs'),
                       'controls': (lic.get('controls') or {}).get('checks'),
                       'verdict': lic.get('verdict')},
        'D4_depth3': {'nodes': d3.get('n_depth2_nodes'), 'scanned': d3.get('n_scanned_nodes'),
                      'abstain': len(d3.get('abstain') or []), 'edges': d3.get('n_edges'),
                      'distinct': d3.get('n_distinct'), 'two_faces': d3.get('two_faces'),
                      're_enters_archive': (d3.get('re_enters_archive') or {}).get('n'),
                      'conservation': d3.get('conservation'), 'verdict': d3.get('verdict')},
        'face': {'total': face.get('total'), 'passed': face.get('passed'),
                 'manifest_sha12': face.get('manifest_sha12'),
                 'instrument_sha12': face.get('instrument_sha12'),
                 'failed': [r['id'] for r in (face.get('results') or []) if not r.get('pass')],
                 'trace': {k: (face.get('side_effect_attribution') or {}).get('trace', {}).get(k)
                           for k in ('commands', 'log_bytes', 'capped')}},
        'gate': gate.get('formal_gate'),
    }
    row = {
        'round': ROUND,
        'ts': subprocess.run(['date', '+%Y-%m-%dT%H:%M%z'], capture_output=True, text=True).stdout.strip(),
        'kind': ('self-check / 逐跑变化语义叶定位(面差分三跑) + 遮蔽族扩容(投影口径断点) + '
                 '提交态核验器 pin 语义对齐 + r444 投影 pin 器具派生复验 + 87 件许可逐件复核 + '
                 'depth-3 独立预注册轮 (60m 自检作业, 不占主线轮号)'),
        'artifact': ('eval/capability/exp1-q35/{prereg_q35.json,run_face_t123.sh,face_q35_t{1,2,3}.json,'
                     'face_delta_q35.py,face_delta_q35.json,license_audit_q35.py,license_audit_q35.json,'
                     'depth3_recursion_q35.py,depth3_recursion_q35.json,verdict_q35_gate.json,'
                     'append_kpi_q35.py,append_ledger_q35.py}; '
                     'eval/capability/{projection_rules.json,face_record_canon.py,instruments.json,'
                     'instruments-check.json}; '
                     'eval/capability/exp1-q30/check_committed_state_q30.py; docs/verification-registry.json; '
                     'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md (附录 AJ)'),
        'change': gate.get('change_text'),
        'readings': readings,
        'honest_boundaries': gate.get('honest_boundaries'),
        'next': gate.get('next_candidates'),
        'owner_round': ROUND,
    }
    path = os.path.join(ROOT, KPI)
    existing = [ln for ln in open(path, encoding='utf-8-sig').read().splitlines() if ln.strip()]
    if any(json.loads(ln).get('round') == ROUND for ln in existing):
        print('IDEMPOTENT: %s 行已存在, 不追加' % ROUND)
        return 0
    keys_existing = set(json.loads(existing[-1]).keys())
    assert set(row.keys()) == keys_existing, ('键集不对齐', set(row.keys()) ^ keys_existing)
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + '\n')
    back = [json.loads(ln) for ln in open(path, encoding='utf-8-sig').read().splitlines() if ln.strip()]
    assert back[-1]['round'] == ROUND and len(back) == len(existing) + 1
    print('APPENDED %s rows=%d (readback ok)' % (ROUND, len(back)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
