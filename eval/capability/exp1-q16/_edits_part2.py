#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q16 · part 2：夹具（嵌套累加正控/负控 + 无类型跳过 fail-closed）与命名开关。"""
import pathlib, sys

P = pathlib.Path('eval/capability/exp1-q16/unit_axis_guard.py')
s = P.read_text(encoding='utf-8')
if 'FX11_nested_loop_replay' in s:
    print('ALREADY_APPLIED'); sys.exit(0)

EDITS = []

# --- 用法行
EDITS.append((
    "  python3 eval/capability/exp1-q15/unit_axis_guard.py --selftest\n"
    "  python3 eval/capability/exp1-q15/unit_axis_guard.py --run [--json OUT]",
    "  python3 eval/capability/exp1-q16/unit_axis_guard.py --selftest\n"
    "  python3 eval/capability/exp1-q16/unit_axis_guard.py --run [--json OUT]"))

# --- 夹具语料：带 symbol_faces 字典 + 独立参考实现
EDITS.append((
    "def _emit_std(rows, sym_strength='weak'):",
    "def _fx_rows_faces():\n"
    "    \"\"\"FX11/FX12 语料：在标准语料上给每条 live 行加 `symbol_faces` 字典（值=rung）。\n"
    "    形状对齐真文件（真文件 `c[\"symbol_faces\"]` 是 符号→rung 的字典）。\"\"\"\n"
    "    rows = _fx_rows()\n"
    "    rungs = ('code_mention', 'noncode_mention', 'declared_type')\n"
    "    for i, r in enumerate(rows):\n"
    "        if r['kind'] != 'code' or r['in_code_fence']:\n"
    "            r['symbol_faces'] = {}\n"
    "            continue\n"
    "        r['symbol_faces'] = {f'S{i}_{j}': rungs[(i + j) % len(rungs)]\n"
    "                             for j in range(1 + (i % 3))}\n"
    "    return rows\n"
    "\n"
    "\n"
    "def _ref_face_rungs(rows):\n"
    "    \"\"\"夹具独立参考实现：**嵌套累加**（外行 × 内字典值）的 rung 分布，与被测派生引擎零共享。\"\"\"\n"
    "    c = collections.Counter()\n"
    "    for r in rows:\n"
    "        if r['kind'] != 'code' or r['in_code_fence']:\n"
    "            continue\n"
    "        for v in (r.get('symbol_faces') or {}).values():\n"
    "            c[v] += 1\n"
    "    return dict(c)\n"
    "\n"
    "\n"
    "def _emit_std(rows, sym_strength='weak'):"))

# --- 新增夹具 FX11/FX12/FX13
EDITS.append((
    "    cases.append({'id': 'FX10_legit_other_names', 'expect_exit': 0, 'dir': d,\n"
    "                  'emitted': {'strong_symbol_kind_counts': dict(_ref_kinds(rows, 'strong')),\n"
    "                              'edge_kind_counts': {'cross_file': _ref_edge_kinds(rows)},\n"
    "                              'edge_weak_n': _ref_edges(rows, 'weak'),\n"
    "                              'edge_strong_n': _ref_edges(rows, 'strong'), 'kind_conserved': True},\n"
    "                  'expect_findings': []})\n"
    "    return cases",
    "    cases.append({'id': 'FX10_legit_other_names', 'expect_exit': 0, 'dir': d,\n"
    "                  'emitted': {'strong_symbol_kind_counts': dict(_ref_kinds(rows, 'strong')),\n"
    "                              'edge_kind_counts': {'cross_file': _ref_edge_kinds(rows)},\n"
    "                              'edge_weak_n': _ref_edges(rows, 'weak'),\n"
    "                              'edge_strong_n': _ref_edges(rows, 'strong'), 'kind_conserved': True},\n"
    "                  'expect_findings': []})\n"
    "\n"
    "    # ---- v1.1 新增：循环累加型计数重放（嵌套累加 + 类型化原因）\n"
    "    LOOP_FACES = ('face_rungs = Counter()\\n'\n"
    "                  'for c in live_code:\\n'\n"
    "                  '    for _rung in (c.get(\"symbol_faces\") or {}).values():\\n'\n"
    "                  '        face_rungs[_rung] += 1\\n')\n"
    "    RET_FACES = RET_STD + '\\n' + '        \"symbol_face_rungs\": dict(face_rungs),'\n"
    "    TOT_FACES = ('n_weak_symbols_classified = sum(len(c[\"kind_per_symbol\"]) '\n"
    "                 'for c in live_code if c[\"edge_strength\"] == EDGE_WEAK)')\n"
    "\n"
    "    # FX11 正控：嵌套累加（内层 iterable 依赖外层变量）⇒ 必须 exit 0 **且 C1 覆盖包装键**\n"
    "    rows11 = _fx_rows_faces()\n"
    "    _, rows11, d11 = _write_fixture(tmp / 'fx11', 'if c[\"edge_strength\"] == EDGE_WEAK',\n"
    "                                    'kind_conserved', TOT_FACES, RET_FACES, rows=rows11,\n"
    "                                    loop_src=LOOP_FACES)\n"
    "    em11 = dict(_emit_std(rows11))\n"
    "    em11['symbol_face_rungs'] = _ref_face_rungs(rows11)\n"
    "    cases.append({'id': 'FX11_nested_loop_replay', 'expect_exit': 0, 'dir': d11,\n"
    "                  'emitted': em11, 'expect_findings': [],\n"
    "                  'expect_c1_equal_keys': ['symbol_face_rungs']})\n"
    "\n"
    "    # FX12 负控：同一生产者，登记值被污染（某 rung +1）⇒ C1 必须报「不一致」（exit 3）\n"
    "    _, rows12, d12 = _write_fixture(tmp / 'fx12', 'if c[\"edge_strength\"] == EDGE_WEAK',\n"
    "                                    'kind_conserved', TOT_FACES, RET_FACES, rows=_fx_rows_faces(),\n"
    "                                    loop_src=LOOP_FACES)\n"
    "    em12 = dict(em11)\n"
    "    _fr = dict(_ref_face_rungs(rows12))\n"
    "    _k0 = sorted(_fr)[0]\n"
    "    _fr[_k0] = _fr[_k0] + 1\n"
    "    em12['symbol_face_rungs'] = _fr\n"
    "    cases.append({'id': 'FX12_nested_loop_registered_corrupted', 'expect_exit': 3, 'dir': d12,\n"
    "                  'emitted': em12, 'expect_findings': ['MEASUREMENT'],\n"
    "                  'expect_msg_contains': '重放与登记读数不一致'})\n"
    "\n"
    "    # FX13 负控：**非**循环累加型计数，过滤引用未定义名 ⇒ 无类型化原因 ⇒ fail-closed exit 3\n"
    "    _, rows13, d13 = _write_fixture(\n"
    "        tmp / 'fx13', 'if c[\"edge_strength\"] == EDGE_WEAK', 'kind_conserved',\n"
    "        'n_weak_symbols_classified = sum(len(c[\"kind_per_symbol\"]) '\n"
    "        'for c in live_code if mystery_gate(c))', RET_STD)\n"
    "    cases.append({'id': 'FX13_untyped_skip_fail_closed', 'expect_exit': 3, 'dir': d13,\n"
    "                  'emitted': _emit_std(rows13), 'expect_findings': ['MEASUREMENT'],\n"
    "                  'expect_msg_contains': '未派生名'})\n"
    "    return cases"))

# --- 自检 harness：支持 expect_msg_contains / expect_c1_equal_keys
EDITS.append((
    "        if c['dir'] is None:\n"
    "            try:\n"
    "                guard(tmp / 'nope.py', tmp / 'nope.jsonl', tmp / 'nope.json')\n"
    "                got, names = 0, ['NO_RAISE']\n"
    "            except MeasurementError:\n"
    "                got, names = 3, ['MEASUREMENT']",
    "        c1_keys = {}\n"
    "        if c['dir'] is None:\n"
    "            try:\n"
    "                guard(tmp / 'nope.py', tmp / 'nope.jsonl', tmp / 'nope.json')\n"
    "                got, names = 0, ['NO_RAISE']\n"
    "            except MeasurementError:\n"
    "                got, names = 3, ['MEASUREMENT']"))

EDITS.append((
    "                v = guard(c['dir'] / 'producer.py', c['dir'] / 'citations.jsonl', emit_path)\n"
    "                got = v['exit']\n"
    "                names = sorted(v['findings'].keys())\n"
    "            except MeasurementError as exc:\n"
    "                got, names = 3, ['MEASUREMENT:' + str(exc)[:60]]",
    "                v = guard(c['dir'] / 'producer.py', c['dir'] / 'citations.jsonl', emit_path)\n"
    "                got = v['exit']\n"
    "                names = sorted(v['findings'].keys())\n"
    "                c1_keys = {r['emitted_key']: r['equal'] for r in v['C1_replay']['rows']}\n"
    "            except MeasurementError as exc:\n"
    "                got, names = 3, ['MEASUREMENT', 'MEASUREMENT:' + str(exc)[:120]]"))

EDITS.append((
    "        want = set(c['expect_findings'])\n"
    "        ok = (got == c['expect_exit']) and all(n in names for n in want)\n"
    "        extra = [n for n in names if n not in want and n != 'C5_ungated_axes']\n"
    "        res.append({'fixture': c['id'], 'expect_exit': c['expect_exit'], 'exit': got,\n"
    "                    'expect_findings': sorted(want), 'findings': names,\n"
    "                    'unexpected_findings': sorted(extra), 'pass': bool(ok)})",
    "        want = set(c['expect_findings'])\n"
    "        msg_ok = (not c.get('expect_msg_contains')) or any(\n"
    "            c['expect_msg_contains'] in n for n in names)\n"
    "        c1_ok = all(c1_keys.get(k) is True for k in (c.get('expect_c1_equal_keys') or []))\n"
    "        ok = (got == c['expect_exit']) and all(n in names for n in want) and msg_ok and c1_ok\n"
    "        extra = [n for n in names if n not in want and n != 'C5_ungated_axes'\n"
    "                 and not n.startswith('MEASUREMENT:')]\n"
    "        res.append({'fixture': c['id'], 'expect_exit': c['expect_exit'], 'exit': got,\n"
    "                    'expect_findings': sorted(want), 'findings': names,\n"
    "                    'expect_msg_contains': c.get('expect_msg_contains'), 'msg_ok': msg_ok,\n"
    "                    'c1_equal_keys': {k: c1_keys.get(k)\n"
    "                                      for k in (c.get('expect_c1_equal_keys') or [])},\n"
    "                    'unexpected_findings': sorted(extra), 'pass': bool(ok)})"))

# --- 自检产物命名与版本串
EDITS.append((
    "    out = {'schema': 'exp1-q15-selftest/1', 'instrument': 'unit_axis_guard.py v1.0',",
    "    out = {'schema': 'exp1-q16-selftest/1', 'instrument': 'unit_axis_guard.py v1.1 (EXP1-Q16)',"))

EDITS.append((
    "    (OUT_DIR / 'selftest_q15.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')",
    "    (OUT_DIR / 'selftest_q16.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')"))

# --- CLI 默认值与产物 schema
EDITS.append((
    "    ap.add_argument('--json', default=str(OUT_DIR / 'verdict_q15.json'))",
    "    ap.add_argument('--json', default=str(OUT_DIR / 'verdict_q16.json'))"))

EDITS.append((
    "    out = {'schema': 'exp1-q15-verdict/1', 'instrument': 'unit_axis_guard.py v1.0 (EXP1-Q15)',",
    "    out = {'schema': 'exp1-q16-verdict/1', 'instrument': 'unit_axis_guard.py v1.1 (EXP1-Q16)',"))

for i, (old, new) in enumerate(EDITS, 1):
    n = s.count(old)
    assert n == 1, f'edit #{i}: 锚点出现 {n} 次（应为 1）\n---\n{old[:200]}'
    s = s.replace(old, new)
print(f'PASS part2: {len(EDITS)} edits applied')
P.write_text(s, encoding='utf-8')
