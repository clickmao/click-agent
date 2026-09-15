#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q16 诊断：C1 新暴露的 symbol_face_rungs / n_symbol_faces 不一致，先查派生/总体链。
只读、不改判据。输出：归档面字段情况 + 重放值 vs 登记值 + 逐 rung 差。
"""
import importlib.util, json, pathlib, collections

spec = importlib.util.spec_from_file_location('uag', 'eval/capability/exp1-q16/unit_axis_guard.py')
uag = importlib.util.module_from_spec(spec); spec.loader.exec_module(uag)

SRC = pathlib.Path('eval/capability/exp1-q10/probe_v260.py')
CITES = pathlib.Path('eval/capability/exp1-q10/citations.jsonl')
EMIT = pathlib.Path('eval/capability/exp1-q10/attribution_q10.json')

tree = uag._parse(SRC)
consts = uag.collect_constants(tree)
pops = uag.collect_populations(tree)
defs = uag.collect_counters(tree)
emitted = json.loads(EMIT.read_text(encoding='utf-8'))
emap = uag.collect_emitted_map(tree, emitted.keys())
dict_maps = uag.collect_dict_maps(tree)
amap, amap_src = uag.derive_archive_map(tree, SRC, CITES, dict_maps)
amap = {k: pathlib.Path(v) for k, v in amap.items()}
amap['citations'] = CITES
added, inherited = uag.inherit_upstream_aliases(pops, amap)
amap.update(added)
cache = {}

out = {'archive_map': {k: str(v) for k, v in sorted(amap.items())},
       'archive_map_source': amap_src, 'alias_inherited': sorted(inherited)}

rows = uag.resolve_rows(pops, consts, amap, cache, 'live_code')
out['live_code_rows'] = len(rows)
out['row_keys'] = sorted(rows[0].keys()) if rows else []
out['rows_with_symbol_faces'] = sum(1 for r in rows if r.get('symbol_faces'))
out['symbol_faces_sample'] = [r.get('symbol_faces') for r in rows[:3] if r.get('symbol_faces')]

# 归档行上的嵌套累加（仪器口径）
rep = collections.Counter()
for r in rows:
    for v in (r.get('symbol_faces') or {}).values():
        rep[v] += 1
reg = emitted.get('symbol_face_rungs')
out['replayed'] = dict(rep)
out['registered'] = reg
out['registered_n_symbol_faces'] = emitted.get('n_symbol_faces')
out['diff'] = {k: [ (reg or {}).get(k), rep.get(k) ] for k in sorted(set(reg or {}) | set(rep))}

# 生产者自身口径：face_rungs 遍历的 live_code 与归档 live_code 是否同源
d_face = defs.get('face_rungs')
out['face_rungs_def'] = {k: v for k, v in (d_face or {}).items() if k != 'filters'}
out['face_rungs_filters'] = (d_face or {}).get('filters')

print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])
pathlib.Path('eval/capability/exp1-q16/diag_face_rungs.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
