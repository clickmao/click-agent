#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q16 · 把 v1.0（q15 冻结件）逐点改写为 v1.1。

纪律：每一处替换断言「旧串恰好出现 1 次」，脚本幂等（重跑检测已改写标记）；
不做整文件重排（避免 diff 淹没真实改动）。
"""
import pathlib, sys

P = pathlib.Path('eval/capability/exp1-q16/unit_axis_guard.py')
s = P.read_text(encoding='utf-8')
if 'v1.1 (EXP1-Q16)' in s:
    print('ALREADY_APPLIED'); sys.exit(0)

EDITS = []

# --- A1 头部 docstring
EDITS.append((
    '"""EXP1-Q15 · §L.7 #3 —— 计数「单位轴 / 口径域」一等不变量（单位分隔机检）v1.0',
    '"""EXP1-Q16 · §L.8 #3 —— 计数「单位轴 / 口径域」一等不变量（单位分隔机检）v1.1\n'
    'v1.1 增量（v1.0 语义零改动，纯加法）：\n'
    '  C11 不可重放必带类型化原因 —— 重放失败的**循环累加型**计数必须归入闭集原因\n'
    '      （SELF_REFERENTIAL_CROSS_ARTIFACT / PARAM_SCOPE / POPULATION_NOT_ARCHIVED /\n'
    '       LOOP_SHAPE_UNMODELED）；归不进去即 fail-closed（exit 3），不允许笼统跳过。\n'
    '  嵌套累加建模 —— 记录**外层 For 绑定链**（内层 iterable 依赖外层变量者现可重放）。'))

# --- A2 OUT_DIR
EDITS.append((
    "OUT_DIR = ROOT / 'eval/capability/exp1-q15'",
    "OUT_DIR = ROOT / 'eval/capability/exp1-q16'"))

# --- A3 常量与辅助函数（父链 / 形参 / 类型化原因）
EDITS.append((
    'class MeasurementError(Exception):\n'
    '    """测量/环境失败（exit 3）—— 绝不与断言失败同码。"""',
    'class MeasurementError(Exception):\n'
    '    """测量/环境失败（exit 3）—— 绝不与断言失败同码。"""\n'
    '\n'
    '\n'
    'UNREPLAYABLE_REASONS = (\'SELF_REFERENTIAL_CROSS_ARTIFACT\', \'PARAM_SCOPE\',\n'
    '                        \'POPULATION_NOT_ARCHIVED\', \'LOOP_SHAPE_UNMODELED\')\n'
    '\n'
    '\n'
    'def collect_param_names(tree):\n'
    '    """生产者函数形参名 —— 形参总体是**外部输入**（不在归档语料面内）⇒ 类型化原因用。"""\n'
    '    return {a.arg for a in ast.walk(tree) if isinstance(a, ast.arg)}\n'
    '\n'
    '\n'
    'def _parent_map(tree):\n'
    '    """ast.walk 不提供父指针 ⇒ 自建（嵌套循环链需要）。"""\n'
    '    parents = {}\n'
    '    for node in ast.walk(tree):\n'
    '        for child in ast.iter_child_nodes(node):\n'
    '            parents[id(child)] = node\n'
    '    return parents\n'
    '\n'
    '\n'
    'def _for_head(f):\n'
    '    tgt = f.target\n'
    '    if isinstance(tgt, ast.Name):\n'
    '        names = [tgt.id]\n'
    '    elif isinstance(tgt, ast.Tuple):\n'
    '        names = [ast.unparse(e) for e in tgt.elts]\n'
    '    else:\n'
    '        names = []\n'
    '    return {\'names\': names, \'iter\': ast.unparse(f.iter)}\n'
    '\n'
    '\n'
    'def enclosing_fors(node, parents):\n'
    '    """自 node 向上的**全部** For 祖先（外层在前）= 嵌套累加的外层绑定链。"""\n'
    '    chain = []\n'
    '    cur = parents.get(id(node))\n'
    '    while cur is not None:\n'
    '        if isinstance(cur, ast.For):\n'
    '            chain.append(cur)\n'
    '        cur = parents.get(id(cur))\n'
    '    return list(reversed(chain))\n'
    '\n'
    '\n'
    'def classify_unreplayable(d, pops, consts, archive_map, cache, param_names):\n'
    '    """把一次重放失败归到闭集里的**一条类型化原因**；归不进去返回 None（调用方 fail-closed）。\n'
    '    判据全部取自派生事实（元素/过滤/迭代根名字面 + 总体可解析性），不猜语义。"""\n'
    '    text = [d.get(\'element\') or \'\'] + list(d.get(\'filters\') or []) + \\\n'
    '           [it[\'iter\'] for it in (d.get(\'iters\') or [])]\n'
    '    if any(\'r1[\' in t for t in text):\n'
    '        return \'SELF_REFERENTIAL_CROSS_ARTIFACT\'\n'
    '    iters = d.get(\'iters\') or []\n'
    '    if iters:\n'
    '        root = base_name(iters[0][\'iter\'].split(\'.\')[0].split(\'(\')[0].strip())\n'
    '        if root and root in param_names:\n'
    '            return \'PARAM_SCOPE\'\n'
    '    if d.get(\'from_loop\'):\n'
    '        if iters:\n'
    '            try:\n'
    '                resolve_rows(pops, consts, archive_map, cache, iters[0][\'iter\'])\n'
    '            except MeasurementError:\n'
    '                return \'POPULATION_NOT_ARCHIVED\'\n'
    '        return \'LOOP_SHAPE_UNMODELED\'\n'
    '    if d.get(\'local_scope\'):\n'
    '        return \'PARAM_SCOPE\'\n'
    '    if d.get(\'self_referential\'):\n'
    '        return \'SELF_REFERENTIAL_CROSS_ARTIFACT\'\n'
    '    return None'))

# --- A4 循环累加：记录外层绑定链
EDITS.append((
    '    for node in ast.walk(tree):\n'
    '        # d) 循环累加型计数: for x[, y] in <iter>[: if <cond>]: <name>[<key>] += 1\n'
    '        if isinstance(node, ast.For):\n'
    '            tgt = node.target\n'
    '            vars_ = [ast.unparse(tgt)] if isinstance(tgt, ast.Name) else (\n'
    '                [ast.unparse(e) for e in tgt.elts] if isinstance(tgt, ast.Tuple) else [])\n'
    '            conds, augs = [], []\n',
    '    parents = _parent_map(tree)\n'
    '    for node in ast.walk(tree):\n'
    '        # d) 循环累加型计数: for x[, y] in <iter>[: if <cond>]: <name>[<key>] += 1\n'
    '        #    v1.1: 记录**外层 For 绑定链**（嵌套累加的内层 iterable 依赖外层变量）\n'
    '        if isinstance(node, ast.For):\n'
    '            chain = enclosing_fors(node, parents) or [node]\n'
    '            heads = [_for_head(f) for f in chain]\n'
    '            if all(len(h[\'names\']) == 1 for h in heads):\n'
    '                iters = [{\'var\': h[\'names\'][0], \'iter\': h[\'iter\']} for h in heads]\n'
    '                shape_ok = True\n'
    '            else:                       # 多元 target / 形状不可建模 ⇒ 只记本层并标注\n'
    '                h = _for_head(node)\n'
    '                iters = [{\'var\': h[\'names\'][0], \'iter\': h[\'iter\']}] if len(h[\'names\']) == 1 else []\n'
    '                shape_ok = False\n'
    '            vars_ = [it[\'var\'] for it in iters]\n'
    '            conds, augs = [], []\n'))

EDITS.append((
    "                    defs.setdefault(nm, {'name': nm, 'kind': 'counter', 'from_loop': True,\n"
    "                                         'element': ast.unparse(sub.target.slice),\n"
    "                                         'iters': [{'var': v, 'iter': ast.unparse(node.iter)} for v in vars_],\n"
    "                                         'filters': conds})",
    "                    defs.setdefault(nm, {'name': nm, 'kind': 'counter', 'from_loop': True,\n"
    "                                         'element': ast.unparse(sub.target.slice),\n"
    "                                         'iters': iters, 'filters': conds,\n"
    "                                         'loop_depth': len(iters),\n"
    "                                         'loop_shape_modeled': shape_ok})"))

# --- A5 replay：类型化原因
EDITS.append((
    'def replay(defs, pops, consts, archive_map, cache, extra_ns=None, unreplayable=None):\n'
    '    """重放全部计数定义 ⇒ {name: value}（值为 Counter 时转 dict）。\n'
    '    `extra_ns` 绑定生产者作用域里的名字；**仅当定义文本自引用生产者局部名**（`r1[...]`）时才允许\n'
    '    在求值失败后记入 `unreplayable` 并跳过（可见、且不计入 C1 相等性），其余失败一律上抛。"""',
    'def replay(defs, pops, consts, archive_map, cache, extra_ns=None, unreplayable=None,\n'
    '           unreplayable_typed=None, param_names=None):\n'
    '    """重放全部计数定义 ⇒ {name: value}（值为 Counter 时转 dict）。\n'
    '    v1.1：求值失败时先归**类型化原因**（闭集）；归得进去才允许跳过并登记原因，\n'
    '    归不进去一律上抛（fail-closed），杜绝「笼统跳过」。"""'))

EDITS.append((
    '        except MeasurementError:\n'
    '            # 自引用生产者局部名 / 总体是**函数形参**（外部输入，不在归档语料面内）⇒ 声明为不可重放\n'
    '            if d.get(\'self_referential\') or d.get(\'local_scope\') or d.get(\'from_loop\'):\n'
    '                if unreplayable is not None:\n'
    '                    unreplayable.append(name)\n'
    '                continue\n'
    '            raise',
    '        except MeasurementError:\n'
    '            reason = classify_unreplayable(d, pops, consts, archive_map, cache, param_names or set())\n'
    '            if reason is None:\n'
    '                raise                       # 无类型化原因 ⇒ 不跳过（fail-closed）\n'
    '            if unreplayable is not None:\n'
    '                unreplayable.append(name)\n'
    '            if unreplayable_typed is not None:\n'
    '                unreplayable_typed[name] = reason\n'
    '            continue'))

# --- A6 guard 调用点
EDITS.append((
    '    _unreplayable = []\n'
    '    replayed = replay({n: d for n, d in defs.items() if n in _needed_names(emitted_map, defs, dict_maps)},\n'
    '                      pops, consts, archive_map, cache, extra_ns={\'r1\': emitted},\n'
    '                      unreplayable=_unreplayable)',
    '    _unreplayable, _unreplayable_typed = [], {}\n'
    '    replayed = replay({n: d for n, d in defs.items() if n in _needed_names(emitted_map, defs, dict_maps)},\n'
    '                      pops, consts, archive_map, cache, extra_ns={\'r1\': emitted},\n'
    '                      unreplayable=_unreplayable,\n'
    '                      unreplayable_typed=_unreplayable_typed,\n'
    '                      param_names=collect_param_names(tree))'))

# --- A7 info 初始化
EDITS.append((
    "    info = {'axis_underived': [], 'replay_mismatch': [], 'underived_emitted_keys': [],\n"
    "            'name_unresolved': [], 'hollow_replay': [], 'not_replayable': []}",
    "    info = {'axis_underived': [], 'replay_mismatch': [], 'underived_emitted_keys': [],\n"
    "            'name_unresolved': [], 'hollow_replay': [], 'not_replayable': [],\n"
    "            'not_replayable_reason': {}}"))

# --- A8 C1 循环里登记原因
EDITS.append((
    "            elif bname in _unreplayable:\n"
    "                info['not_replayable'].append(ekey)\n"
    "            continue",
    "            elif bname in _unreplayable:\n"
    "                info['not_replayable'].append(ekey)\n"
    "                info['not_replayable_reason'][ekey] = _unreplayable_typed.get(bname, 'UNCLASSIFIED')\n"
    "            continue"))

# --- A9 C11 机检（插在 hard 判定之前）
EDITS.append((
    "    vacuous = len(axes) < 2 or len(doms) < 2\n"
    "\n"
    "    hard = {n: v for n, v in findings.items() if n.startswith(('C2', 'C3', 'C4', 'C6', 'C7', 'C8'))}",
    "    vacuous = len(axes) < 2 or len(doms) < 2\n"
    "\n"
    "    # --- C11 不可重放必带类型化原因（闭集）；无原因 ⇒ fail-closed\n"
    "    _reasons = dict(info['not_replayable_reason'])\n"
    "    c11 = {'n_skipped': len(_reasons),\n"
    "           'reasons': _reasons,\n"
    "           'closed_set': list(UNREPLAYABLE_REASONS),\n"
    "           'all_typed': all(r in UNREPLAYABLE_REASONS for r in _reasons.values()),\n"
    "           'n_distinct_reasons': len(set(_reasons.values()))}\n"
    "    if not c11['all_typed']:\n"
    "        bad = [k for k, r in _reasons.items() if r not in UNREPLAYABLE_REASONS]\n"
    "        raise MeasurementError(f'不可重放键缺类型化原因: {bad}（fail-closed，不当作通过）')\n"
    "\n"
    "    hard = {n: v for n, v in findings.items() if n.startswith(('C2', 'C3', 'C4', 'C6', 'C7', 'C8'))}"))

# --- A10 verdict 字段
EDITS.append((
    "        'not_replayable': sorted(info['not_replayable']),\n"
    "        'findings': {k: v for k, v in sorted(hard.items())},",
    "        'not_replayable': sorted(info['not_replayable']),\n"
    "        'not_replayable_typed': {k: info['not_replayable_reason'][k]\n"
    "                                 for k in sorted(info['not_replayable_reason'])},\n"
    "        'C11_unreplayable_reason': c11,\n"
    "        'findings': {k: v for k, v in sorted(hard.items())},"))

# --- A11 版本串
EDITS.append((
    "        'instrument': 'unit_axis_guard.py v1.0 (EXP1-Q15)',",
    "        'instrument': 'unit_axis_guard.py v1.1 (EXP1-Q16)',"))

# --- A12 FX_BASE 占位符
EDITS.append((
    'n_weak_edges = sum(1 for c in live_code if c["edge_strength"] == EDGE_WEAK)\n'
    '__COLL__ = (sum(D_EDGE.values()) == n_weak_edges)',
    'n_weak_edges = sum(1 for c in live_code if c["edge_strength"] == EDGE_WEAK)\n'
    '__LOOP__\n'
    '__COLL__ = (sum(D_EDGE.values()) == n_weak_edges)'))

# --- A13 _write_fixture 支持 loop_src（空值⇒整行消失，老夹具源逐字节不变）
EDITS.append((
    "def _write_fixture(dirp, sym_filter, collect_extra, totals_src, returns_src, emitted_override=None,\n"
    "                   rows=None):",
    "def _write_fixture(dirp, sym_filter, collect_extra, totals_src, returns_src, emitted_override=None,\n"
    "                   rows=None, loop_src=''):"))

EDITS.append((
    "    src = (FX_BASE.replace('__SYM_FILTER__', sym_filter)\n"
    "           .replace('__COLL__', collect_extra)\n"
    "           .replace('__TOTALS__', totals_src)\n"
    "           .replace('__RETURNS__', returns_src))",
    "    src = (FX_BASE.replace('__SYM_FILTER__', sym_filter)\n"
    "           .replace('__COLL__', collect_extra)\n"
    "           .replace('__TOTALS__', totals_src)\n"
    "           .replace('__RETURNS__', returns_src)\n"
    "           .replace('__LOOP__\\n', loop_src or ''))"))

for i, (old, new) in enumerate(EDITS, 1):
    n = s.count(old)
    assert n == 1, f'edit #{i}: 锚点出现 {n} 次（应为 1）\n---\n{old[:200]}'
    s = s.replace(old, new)
print(f'PASS part1: {len(EDITS)} edits applied')
P.write_text(s, encoding='utf-8')
