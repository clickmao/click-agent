#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q16 · part 4（v1.2 → v1.3）：把「口径边界」从「值不等」里彻底分离。

v1.2 真跑仍报不一致：重放**没有失败**，而是成功产出空值（归档面缺字段 ⇒ 内层迭代为空）。
⇒ 需要在 C1 比较层再加一门：重放面为空 ∧ 登记非空 ∧ 机检到「派生链读的行字段在归档面全缺」
   ⇒ 判**口径边界**（单列、不计入 all_equal、不判红），否则才是硬 mismatch（fail-closed）。
"""
import pathlib, sys

P = pathlib.Path('eval/capability/exp1-q16/unit_axis_guard.py')
s = P.read_text(encoding='utf-8')
if 'archive_field_gap' in s:
    print('ALREADY_APPLIED'); sys.exit(0)

EDITS = []

# 1) 抽公共helper
EDITS.append((
    "def classify_unreplayable(d, pops, consts, archive_map, cache, param_names):",
    "def archive_field_gap(d, pops, consts, archive_map, cache):\n"
    "    \"\"\"判据可达面 < 计数总体：内层 iterable 读的**行字段**在归档面里一条都没有 ⇒ 返回缺口证据。\n"
    "    字段名由迭代表达式 AST 派生（只认接收者是外层循环变量者），存在性由归档行实测 ⇒ 不猜。\"\"\"\n"
    "    iters = d.get('iters') or []\n"
    "    if len(iters) < 2:\n"
    "        return None\n"
    "    try:\n"
    "        rows = resolve_rows(pops, consts, archive_map, cache, iters[0]['iter'])\n"
    "    except MeasurementError:\n"
    "        return None\n"
    "    outer_vars = {it['var'] for it in iters[:-1]}\n"
    "    fields = set()\n"
    "    for it in iters[1:]:\n"
    "        fields |= _row_field_reads(it['iter'], outer_vars)\n"
    "    if not fields:\n"
    "        return None\n"
    "    present = {f: sum(1 for r in rows if isinstance(r, dict) and f in r) for f in sorted(fields)}\n"
    "    missing = [f for f, n in present.items() if n == 0]\n"
    "    if not missing:\n"
    "        return None\n"
    "    return {'missing_fields': missing, 'n_rows': len(rows), 'field_presence': present}\n"
    "\n"
    "\n"
    "def classify_unreplayable(d, pops, consts, archive_map, cache, param_names):"))

EDITS.append((
    "        # 判据可达面 < 计数总体：内层 iterable 读的行字段在归档面里**一条都没有** ⇒ 口径边界\n"
    "        if rows and len(iters) > 1:\n"
    "            outer_vars = {it['var'] for it in iters[:-1]}\n"
    "            fields = set()\n"
    "            for it in iters[1:]:\n"
    "                fields |= _row_field_reads(it['iter'], outer_vars)\n"
    "            if fields:\n"
    "                present = {f: sum(1 for r in rows if isinstance(r, dict) and f in r)\n"
    "                           for f in sorted(fields)}\n"
    "                missing = [f for f, n in present.items() if n == 0]\n"
    "                if missing:\n"
    "                    return 'ARCHIVE_FACE_FIELD_ABSENT', {\n"
    "                        'missing_fields': missing, 'n_rows': len(rows),\n"
    "                        'field_presence': present}\n"
    "        return 'LOOP_SHAPE_UNMODELED', {}",
    "        gap = archive_field_gap(d, pops, consts, archive_map, cache) if rows else None\n"
    "        if gap:\n"
    "            return 'ARCHIVE_FACE_FIELD_ABSENT', gap\n"
    "        return 'LOOP_SHAPE_UNMODELED', {}"))

# 2) C1 比较层：口径边界分支
EDITS.append((
    "        reg = emitted.get(ekey)\n"
    "        same = (reg == rep)\n"
    "        selfref = bool((defs.get(bname) or {}).get('self_referential'))\n"
    "        c1.append({'emitted_key': ekey, 'source_name': bname, 'reduce': c.get('reduce'),\n"
    "                   'registered': reg, 'replayed': rep, 'equal': same, 'self_referential': selfref})\n"
    "        if not same and not selfref:\n"
    "            info['replay_mismatch'].append(ekey)\n"
    "        elif selfref:\n"
    "            info['hollow_replay'].append(ekey)",
    "        reg = emitted.get(ekey)\n"
    "        same = (reg == rep)\n"
    "        selfref = bool((defs.get(bname) or {}).get('self_referential'))\n"
    "        if not same and not selfref and reg:\n"
    "            # 重放面为空（归档缺字段 ⇒ 内层迭代为空）⇒ 无从比较 ⇒ 判**口径边界**（单列，不判红）\n"
    "            degenerate = rep is None or rep == {} or rep == 0\n"
    "            gap = archive_field_gap(defs.get(bname) or {}, pops, consts, archive_map, cache) \\\n"
    "                if degenerate else None\n"
    "            if gap:\n"
    "                info['not_replayable'].append(ekey)\n"
    "                info['not_replayable_reason'][ekey] = 'ARCHIVE_FACE_FIELD_ABSENT'\n"
    "                info['not_replayable_detail'][ekey] = gap\n"
    "                c1.append({'emitted_key': ekey, 'source_name': bname, 'reduce': c.get('reduce'),\n"
    "                           'registered': reg, 'replayed': rep, 'equal': None,\n"
    "                           'boundary': 'ARCHIVE_FACE_FIELD_ABSENT'})\n"
    "                continue\n"
    "        c1.append({'emitted_key': ekey, 'source_name': bname, 'reduce': c.get('reduce'),\n"
    "                   'registered': reg, 'replayed': rep, 'equal': same, 'self_referential': selfref})\n"
    "        if not same and not selfref:\n"
    "            info['replay_mismatch'].append(ekey)\n"
    "        elif selfref:\n"
    "            info['hollow_replay'].append(ekey)"))

# 3) C1 汇总：边界单列，all_equal 只覆盖可比较者
EDITS.append((
    "        'C1_replay': {'checked': len(c1), 'all_equal': all(x['equal'] for x in c1),\n"
    "                      'n_self_referential': sum(1 for x in c1 if x['self_referential']),",
    "        'C1_replay': {'checked': len(c1),\n"
    "                      'n_boundary': sum(1 for x in c1 if x['equal'] is None),\n"
    "                      'all_equal': all(x['equal'] for x in c1 if x['equal'] is not None),\n"
    "                      'n_self_referential': sum(1 for x in c1 if x['self_referential']),"))

# 4) 版本：v1.3
EDITS.append((
    "        'instrument': 'unit_axis_guard.py v1.2 (EXP1-Q16)',",
    "        'instrument': 'unit_axis_guard.py v1.3 (EXP1-Q16)',"))
EDITS.append((
    "    out = {'schema': 'exp1-q16-selftest/1', 'instrument': 'unit_axis_guard.py v1.2 (EXP1-Q16)',",
    "    out = {'schema': 'exp1-q16-selftest/1', 'instrument': 'unit_axis_guard.py v1.3 (EXP1-Q16)',"))
EDITS.append((
    "    out = {'schema': 'exp1-q16-verdict/1', 'instrument': 'unit_axis_guard.py v1.2 (EXP1-Q16)',",
    "    out = {'schema': 'exp1-q16-verdict/1', 'instrument': 'unit_axis_guard.py v1.3 (EXP1-Q16)',"))
EDITS.append((
    "v1.1 增量（v1.0 语义零改动，纯加法）：",
    "v1.3 增量（v1.0 语义零改动，纯加法；v1.1/v1.2 为同轮内演进）：\n"
    "  口径边界单列 —— 重放面为空 ∧ 登记非空 ∧ 机检到「派生链读的行字段在归档面全缺」\n"
    "      ⇒ 记 ARCHIVE_FACE_FIELD_ABSENT（C1 的 n_boundary 单列，不计入 all_equal、不判红）；\n"
    "      无该证据时仍是硬 mismatch（fail-closed）。\n"
    "v1.1 增量（v1.0 语义零改动，纯加法）："))

for i, (old, new) in enumerate(EDITS, 1):
    n = s.count(old)
    assert n == 1, f'edit #{i}: 锚点出现 {n} 次（应为 1）\n---\n{old[:200]}'
    s = s.replace(old, new)
print(f'PASS part4: {len(EDITS)} edits applied')
P.write_text(s, encoding='utf-8')
