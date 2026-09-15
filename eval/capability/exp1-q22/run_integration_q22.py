#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q22 · 集成零回归判定 (P8): 新闸下跑的 L2 子集 vs 归档全量面 (Q21 那次) 的**同名行**逐位比对。

为什么只比子集: 对侧 R465 (门控延迟探针) + dotnet build 在飞 ⇒ 本侧不得跑全量面
(probe.run_probe 会拉起 llama-server, 与对侧测量互污)。子集覆盖含 `l2.instruments-check`
的嵌套行 —— 正是本轮新增机制所在。
白名单 (先声明后比对): 仅 `sha12` 字段对被本轮改动的器具行 (l2.instruments-check) 放行。
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREV = HERE / 'face_prev_q21.json'
NEW = HERE / 'l2_face_scoped_q22.json'
WHITELIST_FIELDS_BY_ROW = {'l2.instruments-check': {'sha12'}}


def nc_sig(rec):
    return [(n['cmd'], n['rc'], n['expect'], n['pass']) for n in rec.get('negative_controls', [])]


def main():
    if len(sys.argv) > 1:
        new_path = pathlib.Path(sys.argv[1])
    else:
        new_path = NEW
    prev = json.loads(PREV.read_text(encoding='utf-8'))
    new = json.loads(new_path.read_text(encoding='utf-8'))
    pmap = {r['id']: r for r in prev['results']}
    nmap = {r['id']: r for r in new['results']}
    shared = sorted(set(pmap) & set(nmap))
    drift, compared = [], []
    for rid in shared:
        p, n = pmap[rid], nmap[rid]
        wl = WHITELIST_FIELDS_BY_ROW.get(rid, set())
        for f in ('rc', 'expect_rc', 'substr_ok', 'pass', 'l2_ok'):
            if f not in wl and p.get(f) != n.get(f):
                drift.append({'id': rid, 'field': f, 'prev': p.get(f), 'new': n.get(f)})
        if 'l2_fields' not in wl and p.get('l2_fields') != n.get('l2_fields'):
            drift.append({'id': rid, 'field': 'l2_fields', 'prev': p.get('l2_fields'), 'new': n.get('l2_fields')})
        if 'negative_controls' not in wl and nc_sig(p) != nc_sig(n):
            drift.append({'id': rid, 'field': 'negative_controls', 'prev': nc_sig(p), 'new': nc_sig(n)})
        if 'sha12' not in wl and p.get('sha12') != n.get('sha12'):
            drift.append({'id': rid, 'field': 'sha12', 'prev': p.get('sha12'), 'new': n.get('sha12')})
        if not [d for d in drift if d['id'] == rid]:
            compared.append(rid)
    gate = new.get('side_effect_attribution') or {}
    rep = {
        'round': 'EXP1-Q22', 'schema': 'q22-integration/1',
        'prev_face': prev.get('schema'), 'new_face': new.get('schema'),
        'prev_batch': {'passed': prev.get('passed'), 'total': prev.get('total'),
                       'side_effects': prev.get('side_effects')},
        'new_batch': {'passed': new.get('passed'), 'total': new.get('total'),
                      'side_effects': new.get('side_effects')},
        'new_gate': {
            'verdict': gate.get('verdict'), 'measurement_ok': gate.get('measurement_ok'),
            'self_n': len(gate.get('self_writes') or []),
            'foreign': [w['path'] for w in gate.get('foreign_writes') or []],
            'foreign_live_fd': {w['path']: [e['pid'] for e in w.get('live_fd', [])]
                                for w in gate.get('foreign_writes') or []},
            'pre_existing_n': len(gate.get('pre_existing') or []),
            'old_gate_false_reds': gate.get('old_gate_false_reds') or [],
            'conservation': gate.get('conservation'),
            'trace': {k: v for k, v in (gate.get('trace') or {}).items() if k != 'raw_paths_sample'},
            'census_n': len(gate.get('census_in_repo_cwd') or []),
        },
        'shared_ids': shared, 'compared_clean': compared, 'uncompared_ids': sorted(set(pmap) - set(nmap)),
        'whitelist': {k: sorted(v) for k, v in WHITELIST_FIELDS_BY_ROW.items()},
        'drift': drift,
        'P8_pass': bool(shared and not drift and new.get('passed') == new.get('total')
                        and not (new.get('side_effects') or [])
                        and gate.get('measurement_ok') is True),
    }
    (HERE / 'integration_q22.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1) + '\n',
                                              encoding='utf-8')
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0 if rep['P8_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
