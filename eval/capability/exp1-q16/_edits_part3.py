#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q16 · part 3（v1.1 → v1.2）：真跑暴露的**测量层归并缺陷**修正。

v1.1 真跑在 attribution_q10.json 上抛「重放与登记读数不一致」（symbol_face_rungs / n_symbol_faces）。
诊断（diag_face_rungs.json）证明真因不是「算错」而是两类原因被并成一类：
  归档语料 928 条 live 行的**字段集合里没有 `symbol_faces`**（rows_with_symbol_faces = 0），
  而登记读数正是对该字段的计数 ⇒ **判据可达面 < 计数总体**（口径边界），不是值不等。
本步把「字段不在归档面」独立成类型化原因，并把「值不等」保留为硬失败。
"""
import pathlib, sys

P = pathlib.Path('eval/capability/exp1-q16/unit_axis_guard.py')
s = P.read_text(encoding='utf-8')
if 'ARCHIVE_FACE_FIELD_ABSENT' in s:
    print('ALREADY_APPLIED'); sys.exit(0)

EDITS = []

EDITS.append((
    "UNREPLAYABLE_REASONS = ('SELF_REFERENTIAL_CROSS_ARTIFACT', 'PARAM_SCOPE',\n"
    "                        'POPULATION_NOT_ARCHIVED', 'LOOP_SHAPE_UNMODELED')",
    "UNREPLAYABLE_REASONS = ('SELF_REFERENTIAL_CROSS_ARTIFACT', 'PARAM_SCOPE',\n"
    "                        'POPULATION_NOT_ARCHIVED', 'LOOP_SHAPE_UNMODELED',\n"
    "                        'ARCHIVE_FACE_FIELD_ABSENT')"))

EDITS.append((
    "def classify_unreplayable(d, pops, consts, archive_map, cache, param_names):",
    "def _row_field_reads(expr_src, outer_vars):\n"
    "    \"\"\"从迭代表达式里抽「读**归档行**字段」的字段名 —— 仅认接收者是外层循环变量者\n"
    "    （`c.get(\"f\")` / `c[\"f\"]`），避免把嵌套字典的键误当行字段。\"\"\"\n"
    "    try:\n"
    "        node = ast.parse(expr_src, mode='eval').body\n"
    "    except SyntaxError:\n"
    "        return set()\n"
    "    out = set()\n"
    "    for n in ast.walk(node):\n"
    "        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)\n"
    "                and n.func.attr == 'get' and isinstance(n.func.value, ast.Name)\n"
    "                and n.func.value.id in outer_vars\n"
    "                and n.args and isinstance(n.args[0], ast.Constant)\n"
    "                and isinstance(n.args[0].value, str)):\n"
    "            out.add(n.args[0].value)\n"
    "        elif (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)\n"
    "                and n.value.id in outer_vars and isinstance(n.slice, ast.Constant)\n"
    "                and isinstance(n.slice.value, str)):\n"
    "            out.add(n.slice.value)\n"
    "    return out\n"
    "\n"
    "\n"
    "def classify_unreplayable(d, pops, consts, archive_map, cache, param_names):"))

# 分类函数主体：返回 (reason, detail)，新增「归档面缺字段」判据
EDITS.append((
    "    if any('r1[' in t for t in text):\n"
    "        return 'SELF_REFERENTIAL_CROSS_ARTIFACT'\n"
    "    iters = d.get('iters') or []\n"
    "    if iters:\n"
    "        root = base_name(iters[0]['iter'].split('.')[0].split('(')[0].strip())\n"
    "        if root and root in param_names:\n"
    "            return 'PARAM_SCOPE'\n"
    "    if d.get('from_loop'):\n"
    "        if iters:\n"
    "            try:\n"
    "                resolve_rows(pops, consts, archive_map, cache, iters[0]['iter'])\n"
    "            except MeasurementError:\n"
    "                return 'POPULATION_NOT_ARCHIVED'\n"
    "        return 'LOOP_SHAPE_UNMODELED'\n"
    "    if d.get('local_scope'):\n"
    "        return 'PARAM_SCOPE'\n"
    "    if d.get('self_referential'):\n"
    "        return 'SELF_REFERENTIAL_CROSS_ARTIFACT'\n"
    "    return None",
    "    if any('r1[' in t for t in text):\n"
    "        return 'SELF_REFERENTIAL_CROSS_ARTIFACT', {}\n"
    "    iters = d.get('iters') or []\n"
    "    if iters:\n"
    "        root = base_name(iters[0]['iter'].split('.')[0].split('(')[0].strip())\n"
    "        if root and root in param_names:\n"
    "            return 'PARAM_SCOPE', {}\n"
    "    if d.get('from_loop'):\n"
    "        rows = None\n"
    "        if iters:\n"
    "            try:\n"
    "                rows = resolve_rows(pops, consts, archive_map, cache, iters[0]['iter'])\n"
    "            except MeasurementError:\n"
    "                return 'POPULATION_NOT_ARCHIVED', {}\n"
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
    "        return 'LOOP_SHAPE_UNMODELED', {}\n"
    "    if d.get('local_scope'):\n"
    "        return 'PARAM_SCOPE', {}\n"
    "    if d.get('self_referential'):\n"
    "        return 'SELF_REFERENTIAL_CROSS_ARTIFACT', {}\n"
    "    return None, {}"))

# replay：解包 tuple + 详情落盘
EDITS.append((
    "def replay(defs, pops, consts, archive_map, cache, extra_ns=None, unreplayable=None,\n"
    "           unreplayable_typed=None, param_names=None):",
    "def replay(defs, pops, consts, archive_map, cache, extra_ns=None, unreplayable=None,\n"
    "           unreplayable_typed=None, param_names=None, unreplayable_detail=None):"))

EDITS.append((
    "            reason = classify_unreplayable(d, pops, consts, archive_map, cache, param_names or set())\n"
    "            if reason is None:\n"
    "                raise                       # 无类型化原因 ⇒ 不跳过（fail-closed）\n"
    "            if unreplayable is not None:\n"
    "                unreplayable.append(name)\n"
    "            if unreplayable_typed is not None:\n"
    "                unreplayable_typed[name] = reason\n"
    "            continue",
    "            reason, detail = classify_unreplayable(d, pops, consts, archive_map, cache,\n"
    "                                                   param_names or set())\n"
    "            if reason is None:\n"
    "                raise                       # 无类型化原因 ⇒ 不跳过（fail-closed）\n"
    "            if unreplayable is not None:\n"
    "                unreplayable.append(name)\n"
    "            if unreplayable_typed is not None:\n"
    "                unreplayable_typed[name] = reason\n"
    "            if unreplayable_detail is not None and detail:\n"
    "                unreplayable_detail[name] = detail\n"
    "            continue"))

# guard：传递详情 + 落 verdict
EDITS.append((
    "    _unreplayable, _unreplayable_typed = [], {}\n",
    "    _unreplayable, _unreplayable_typed, _unreplayable_detail = [], {}, {}\n"))

EDITS.append((
    "                      unreplayable_typed=_unreplayable_typed,\n"
    "                      param_names=collect_param_names(tree))",
    "                      unreplayable_typed=_unreplayable_typed,\n"
    "                      param_names=collect_param_names(tree),\n"
    "                      unreplayable_detail=_unreplayable_detail)"))

EDITS.append((
    "    info = {'axis_underived': [], 'replay_mismatch': [], 'underived_emitted_keys': [],\n"
    "            'name_unresolved': [], 'hollow_replay': [], 'not_replayable': [],\n"
    "            'not_replayable_reason': {}}",
    "    info = {'axis_underived': [], 'replay_mismatch': [], 'underived_emitted_keys': [],\n"
    "            'name_unresolved': [], 'hollow_replay': [], 'not_replayable': [],\n"
    "            'not_replayable_reason': {}, 'not_replayable_detail': {}}"))

EDITS.append((
    "                info['not_replayable_reason'][ekey] = _unreplayable_typed.get(bname, 'UNCLASSIFIED')",
    "                info['not_replayable_reason'][ekey] = _unreplayable_typed.get(bname, 'UNCLASSIFIED')\n"
    "                if _unreplayable_detail.get(bname):\n"
    "                    info['not_replayable_detail'][ekey] = _unreplayable_detail[bname]"))

EDITS.append((
    "        'not_replayable_typed': {k: info['not_replayable_reason'][k]\n"
    "                                 for k in sorted(info['not_replayable_reason'])},\n"
    "        'C11_unreplayable_reason': c11,",
    "        'not_replayable_typed': {k: info['not_replayable_reason'][k]\n"
    "                                 for k in sorted(info['not_replayable_reason'])},\n"
    "        'not_replayable_detail': info['not_replayable_detail'],\n"
    "        'C11_unreplayable_reason': c11,"))

EDITS.append((
    "        'instrument': 'unit_axis_guard.py v1.1 (EXP1-Q16)',",
    "        'instrument': 'unit_axis_guard.py v1.2 (EXP1-Q16)',"))

EDITS.append((
    "    out = {'schema': 'exp1-q16-selftest/1', 'instrument': 'unit_axis_guard.py v1.1 (EXP1-Q16)',",
    "    out = {'schema': 'exp1-q16-selftest/1', 'instrument': 'unit_axis_guard.py v1.2 (EXP1-Q16)',"))

EDITS.append((
    "    out = {'schema': 'exp1-q16-verdict/1', 'instrument': 'unit_axis_guard.py v1.1 (EXP1-Q16)',",
    "    out = {'schema': 'exp1-q16-verdict/1', 'instrument': 'unit_axis_guard.py v1.2 (EXP1-Q16)',"))

# harness：期望的类型化原因
EDITS.append((
    "        c1_ok = all(c1_keys.get(k) is True for k in (c.get('expect_c1_equal_keys') or []))",
    "        c1_ok = all(c1_keys.get(k) is True for k in (c.get('expect_c1_equal_keys') or []))\n"
    "        typed_ok = all((c.get('expect_typed_reason') or {}).get(k) == c1_keys.get('__typed_' + k)\n"
    "                       for k in (c.get('expect_typed_reason') or {}))"))
EDITS.append((
    "        ok = (got == c['expect_exit']) and all(n in names for n in want) and msg_ok and c1_ok",
    "        ok = (got == c['expect_exit']) and all(n in names for n in want) and msg_ok and c1_ok and typed_ok"))

EDITS.append((
    "                c1_keys = {r['emitted_key']: r['equal'] for r in v['C1_replay']['rows']}",
    "                c1_keys = {r['emitted_key']: r['equal'] for r in v['C1_replay']['rows']}\n"
    "                c1_keys.update({'__typed_' + k: r for k, r in v['not_replayable_typed'].items()})"))

EDITS.append((
    "                    'c1_equal_keys': {k: c1_keys.get(k)\n"
    "                                      for k in (c.get('expect_c1_equal_keys') or [])},",
    "                    'c1_equal_keys': {k: c1_keys.get(k)\n"
    "                                      for k in (c.get('expect_c1_equal_keys') or [])},\n"
    "                    'typed_reasons': {k: c1_keys.get('__typed_' + k)\n"
    "                                      for k in (c.get('expect_typed_reason') or {})},"))

# FX14：归档面缺字段（口径边界）⇒ 类型化豁免，且**不得**与「值不等」同判
EDITS.append((
    "    # FX13 负控：**非**循环累加型计数，过滤引用未定义名 ⇒ 无类型化原因 ⇒ fail-closed exit 3",
    "    # FX14 口径边界：同一嵌套累加，但**归档语料没有该字段** ⇒ 必须类型化为\n"
    "    #   ARCHIVE_FACE_FIELD_ABSENT 并豁免（≠ 值不等）；登记值故意与重放面不同（复刻真文件形态）\n"
    "    _, rows14, d14 = _write_fixture(tmp / 'fx14', 'if c[\"edge_strength\"] == EDGE_WEAK',\n"
    "                                    'kind_conserved', TOT_FACES, RET_FACES, rows=_fx_rows(),\n"
    "                                    loop_src=LOOP_FACES)\n"
    "    em14 = dict(_emit_std(rows14))\n"
    "    em14['symbol_face_rungs'] = _ref_face_rungs(_fx_rows_faces())\n"
    "    cases.append({'id': 'FX14_archive_face_field_absent', 'expect_exit': 0, 'dir': d14,\n"
    "                  'emitted': em14, 'expect_findings': [],\n"
    "                  'expect_typed_reason': {'symbol_face_rungs': 'ARCHIVE_FACE_FIELD_ABSENT'}})\n"
    "\n"
    "    # FX13 负控：**非**循环累加型计数，过滤引用未定义名 ⇒ 无类型化原因 ⇒ fail-closed exit 3"))

for i, (old, new) in enumerate(EDITS, 1):
    n = s.count(old)
    assert n == 1, f'edit #{i}: 锚点出现 {n} 次（应为 1）\n---\n{old[:200]}'
    s = s.replace(old, new)
print(f'PASS part3: {len(EDITS)} edits applied')
P.write_text(s, encoding='utf-8')
