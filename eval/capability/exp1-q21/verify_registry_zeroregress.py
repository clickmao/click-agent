#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q21 · 台账改动的零回归机检: 既有键取值必须逐位不变, 只允许新增键。"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
REG = 'eval/capability/instruments.json'
old = json.loads(subprocess.run(['git', 'show', 'HEAD:' + REG], capture_output=True, text=True,
                                cwd=str(ROOT)).stdout)
new = json.loads((ROOT / REG).read_text(encoding='utf-8'))
o = {r['id']: r for r in old['instruments']}
n = {r['id']: r for r in new['instruments']}
out = {'ids_equal': set(o) == set(n), 'top_level_keys_equal': set(old) == set(new),
       'rows_n': len(n), 'added_keys': {}, 'removed_keys': {}, 'value_drift': []}
# 本轮**唯一**允许的取值变更: 空 input_fingerprint → 由审计钩子派生填充 (本轮的产出本身)。
ALLOWED_VALUE_CHANGES = {('input_fingerprint',)}   # 且仅当旧值为空列表
for rid, rn in n.items():
    ro = o[rid]
    added = sorted(set(rn).difference(ro))
    removed = sorted(set(ro).difference(rn))
    if added:
        out['added_keys'][rid] = added
    if removed:
        out['removed_keys'][rid] = removed
    for k in sorted(set(ro).intersection(rn)):
        if ro[k] != rn[k]:
            allowed = (k == 'input_fingerprint') and ro[k] == []
            out['value_drift'].append({'id': rid, 'key': k, 'allowed': allowed,
                                       'old': ro[k], 'new_len': len(rn[k])})
            if allowed:
                out.setdefault('allowed_changes', []).append({'id': rid, 'key': k, 'filled_n': len(rn[k])})
out['pass'] = bool(out['ids_equal'] and out['top_level_keys_equal']
                   and not out['removed_keys']
                   and all(d['allowed'] for d in out['value_drift']))
pathlib.Path(ROOT / 'eval/capability/exp1-q21/registry_zeroregress.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in out.items() if k not in ('added_keys',)},
                 ensure_ascii=False, indent=1))
print('新增键行数:', len(out['added_keys']), '| 例:', list(out['added_keys'].items())[:2])
sys.exit(0 if out['pass'] else 2)
