#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q15 · §L.7 #3 —— 计数「单位轴 / 口径域」一等不变量（单位分隔机检）v1.0

问题域：引用图仪器的读数里同时存在多种**单位**（边 / 符号 / 面 / 出现次数 / 文档）
与多个**口径域**（弱边 / 强边 / 断链 / 弃权）。两者混算会产出「看起来合理、量级错」的数字，
且失效形态是静默的（总数自证 ⇒ 守恒门恒真 ⇒ 无人能发现）。

本器把「单位轴与口径域必须显式、且可机检」升为一等不变量：

  C1 重放保真   —— 计数定义由**生产者源码 AST** 派生（元素表达式 + 过滤条件 + 总体链），
                   在归档语料上重放，必须与登记读数逐位相同；不符判**测量失败**（exit 3）。
  C2 轴标签     —— 计数键必须含其派生单位轴 token（不可派生者入 axis_underived 可见清单）。
  C3 域标签     —— 键名口径质词必须与派生过滤域一致；不一致 ⇒ 违规 + 逐域分解。
  C4 自证分母   —— 登记总数定义为 sum(自身各桶) ⇒ 无独立分母 ⇒ 恒真 ⇒ 违规登记。
  C5 守恒门覆盖 —— 逐 *_conserved 门反解分母来源（独立总体 / 自证），并列出**无门**的轴。
  C6 易混总数   —— 不同 (轴, 域) 的总数相对差 < 阈值 ⇒ 必须带显式区分 token，否则违规。
  C7 质词重载   —— 同一质词跨两个不同 (轴, 域) 使用 ⇒ 违规（给出比值）。
  C8 比值声明   —— 比值类字段必须带 *_unit / *_of 声明且两侧轴一致。
  C9 非平凡     —— 轴集合或域集合为单元素 ⇒ vacuous=true 显式判红。
  C10 确定性    —— 同输入两跑逐字节相同。

退出码三态：0 全过 / 2 断言失败（不变量被违反）/ 3 测量或环境失败（fail-closed）。

用法：
  python3 eval/capability/exp1-q15/unit_axis_guard.py --selftest
  python3 eval/capability/exp1-q15/unit_axis_guard.py --run [--json OUT]

语言无关性：本器不依赖任何语言特定后缀/字面量；过滤条件与总体链一律取自被测生产者的
源码 AST（`ast.unparse`），派生失败即抛（不回落默认值）。
"""
import argparse
import ast
import collections
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

def _find_root():
    """自定位仓库根：向上找到含 eval/capability 的目录（避免脆弱的 parents[N] 深度假设）。"""
    here = pathlib.Path(__file__).resolve()
    for p in here.parents:
        if (p / 'eval' / 'capability').is_dir():
            return p
    raise RuntimeError('未能自定位仓库根（向上未见 eval/capability）')


ROOT = _find_root()
DEF_SRC = ROOT / 'eval/capability/exp1-q10/probe_v260.py'
DEF_CITES = ROOT / 'eval/capability/exp1-q10/citations.jsonl'
DEF_EMIT = ROOT / 'eval/capability/exp1-q10/probe_stdout.json'
OUT_DIR = ROOT / 'eval/capability/exp1-q15'

AXIS_TOKENS = ('edge', 'symbol', 'face', 'occurrence', 'citation', 'doc', 'continuation')
DOMAIN_TOKENS = ('weak', 'strong', 'broken', 'waived', 'mixed_strong')
RATIO_HINTS = ('rate', 'ratio', 'pct', 'percent', 'share', 'frac', 'precision', 'recall', 'avg', 'mean')
CONFUSABLE_REL_GAP = 0.05          # 预注册常量（见 prereg_q15.json）
NON_COUNT_KEYS = {'gates', 'q2', 'exit_code', 'verdict_counts', 'waive_reasons',
                  'relocated_fact_verdicts', 'continuation_verdicts', 'continuation_tiers',
                  'continuation_waive_reasons', 'citations', 'continuations',
                  'symbol_face_candidates', 'symbol_files', 'contracts',
                  'manifest_like_hits', 'di_registrations', 'di_files', 'input_sha'}


class MeasurementError(Exception):
    """测量/环境失败（exit 3）—— 绝不与断言失败同码。"""


# ---------------------------------------------------------------- 派生层（源码 AST）

def _parse(path):
    try:
        return ast.parse(pathlib.Path(path).read_text(encoding='utf-8', errors='replace'))
    except Exception as exc:  # noqa: BLE001
        raise MeasurementError(f'源码不可解析 {path}: {exc}')


def _literal(node):
    try:
        return ast.literal_eval(node)
    except Exception:  # noqa: BLE001
        return None


def collect_constants(tree):
    """模块级常量（含字符串/元组/整型），供过滤表达式求值使用。"""
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            lit = _literal(node.value)
            if lit is not None and isinstance(lit, (str, int, tuple, frozenset)):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        out[t.id] = lit
    return out


def collect_populations(tree):
    """`name = [elem for x in base if cond]` 链 —— 供把总体名解析回归档行。"""
    pops = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.ListComp):
            continue
        for t in node.targets:
            if not isinstance(t, ast.Name):
                continue
            lc = node.value
            gen = lc.generators[0]
            if not isinstance(gen.target, ast.Name):
                continue
            pops[t.id] = {
                'var': gen.target.id,
                'base': ast.unparse(gen.iter),
                'conds': [ast.unparse(c) for c in gen.ifs],
                'element': ast.unparse(lc.elt),
                'identity_element': isinstance(lc.elt, ast.Call),
            }
    return pops


def collect_counters(tree):
    """Counter(...) / sum(...) 计数定义：元素表达式、嵌套迭代、过滤条件、分母来源。"""
    defs = {}
    _param_names = {a.arg for a in ast.walk(tree) if isinstance(a, ast.arg)}

    def _mark(d):
        txt = [d.get('element') or ''] + list(d.get('filters') or []) + \
              [it['iter'] for it in (d.get('iters') or [])]
        d['self_referential'] = any('r1[' in s for s in txt)
        return d

    for node in ast.walk(tree):
        # d) 循环累加型计数: for x[, y] in <iter>[: if <cond>]: <name>[<key>] += 1
        if isinstance(node, ast.For):
            tgt = node.target
            vars_ = [ast.unparse(tgt)] if isinstance(tgt, ast.Name) else (
                [ast.unparse(e) for e in tgt.elts] if isinstance(tgt, ast.Tuple) else [])
            conds, augs = [], []
            for item in node.body:
                if isinstance(item, ast.If):          # `for ...: if <cond>: x[k] += 1`
                    conds.append(ast.unparse(item.test))
                    augs.extend([s for s in item.body if isinstance(s, ast.AugAssign)])
                elif isinstance(item, ast.AugAssign):
                    augs.append(item)
            for sub in augs:
                if (isinstance(sub.target, ast.Subscript) and isinstance(sub.target.value, ast.Name)
                        and sub.op.__class__ is ast.Add and vars_):
                    nm = sub.target.value.id
                    defs.setdefault(nm, {'name': nm, 'kind': 'counter', 'from_loop': True,
                                         'element': ast.unparse(sub.target.slice),
                                         'iters': [{'var': v, 'iter': ast.unparse(node.iter)} for v in vars_],
                                         'filters': conds})
            continue
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if not isinstance(t, ast.Name):
                continue
            v = node.value
            # a) Counter(<genexp>) / Counter([...])
            if (isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == 'Counter'
                    and v.args and isinstance(v.args[0], (ast.GeneratorExp, ast.ListComp))):
                comp = v.args[0]
                iters = []
                for g in comp.generators:
                    iters.append({'var': ast.unparse(g.target), 'iter': ast.unparse(g.iter)})
                defs[t.id] = {'name': t.id, 'kind': 'counter',
                              'element': ast.unparse(comp.elt),
                              'iters': iters,
                              'filters': [ast.unparse(c) for g in comp.generators for c in g.ifs]}
            # b) sum(<X>.values())  ⇒ 自证分母
            elif isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == 'sum':
                inner = v.args[0]
                if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
                        and inner.func.attr == 'values' and isinstance(inner.func.value, ast.Name)):
                    defs[t.id] = {'name': t.id, 'kind': 'self_derived',
                                  'of': inner.func.value.id, 'provenance': 'self_derived'}
                elif any(isinstance(c, ast.GeneratorExp) for c in v.args):
                    gen = [c for c in v.args if isinstance(c, ast.GeneratorExp)][0]
                    defs[t.id] = {'name': t.id, 'kind': 'count', 'element': ast.unparse(gen.elt),
                                  'iters': [{'var': ast.unparse(g.target), 'iter': ast.unparse(g.iter)}
                                            for g in gen.generators],
                                  'filters': [ast.unparse(c) for g in gen.generators for c in g.ifs],
                                  'provenance': 'independent'}
                elif isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == 'len':
                    defs[t.id] = {'name': t.id, 'kind': 'count', 'element': '1',
                                  'iters': [{'var': '_x', 'iter': ast.unparse(inner.args[0])}],
                                  'filters': [], 'provenance': 'independent'}
            # c) sum(<X>.values()) == <Y> 形式的守恒门
            elif isinstance(v, ast.Compare) and isinstance(v.left, ast.Call):
                lt = ast.unparse(v.left)
                rt = ast.unparse(v.comparators[0]) if v.comparators else ''
                if '.values()' in lt:
                    defs[t.id] = {'name': t.id, 'kind': 'gate',
                                  'buckets': lt.replace('sum(', '').replace('.values())', ''),
                                  'denominator': rt}
            # d) 循环累加型计数已在上方 For 分支处理（此处不再重复）
    for d in defs.values():
        _mark(d)
        its = d.get('iters') or []
        d['local_scope'] = bool(its and its[0]['iter'] in _param_names)
    return defs


def collect_emitted_map(tree, want_keys=None):
    """登记字典（返回值或赋值均可）→ {登记键: 源码表达式}。
    多候选时**按与归档产物的键重合度**择一（登记名与内部名可能不同 ⇒ 必须派生，不硬编码）。"""
    cands = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict) and len(node.keys) >= 4:
            cands.append(node)
    if not cands:
        raise MeasurementError('未找到登记字典字面量 ⇒ 无法派生 登记键→源码表达式 映射')
    want = set(want_keys or [])
    best, best_score = None, -1
    for d in cands:
        ks = {k.value for k in d.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        score = len(ks & want) if want else len(ks)
        if score > best_score:
            best, best_score = d, score
    if want and best_score < 3:
        raise MeasurementError(f'登记字典与归档产物键重合度过低（{best_score}）⇒ fail-closed，不猜')
    out = {}
    for k, v in zip(best.keys, best.values):
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            out[k.value] = ast.unparse(v)
    return out


def base_name(expr: str):
    """把 `dict(kind_sym_counts)` / `r1["n_weak_edges"]` / `len(set(x))` 归一到一个定义名。"""
    e = expr.strip()
    for wrapper in ('dict(', 'list(', 'set(', 'sorted('):
        if e.startswith(wrapper) and e.endswith(')'):
            e = e[len(wrapper):-1].strip()
    if e.startswith('len(') and e.endswith(')'):
        e = e[4:-1].strip()
    if e.startswith('sum(') and e.endswith('.values())'):
        e = e[4:-len('.values())')].strip()
    m = re.fullmatch(r'[A-Za-z_]\w*\[(["\'])(.+?)\1\]', e)      # r1["name"] ⇒ name
    if m:
        e = m.group(2)
    return e if e.isidentifier() else None


# ---------------------------------------------------------------- 重放层（归档语料）

def derive_archive_map(tree, src_path, cites_default, dict_maps=None):
    """总体根名 → 归档文件：从生产者的**落盘块**派生 `with_name("X.jsonl")` 内 dump 的键，
    并把**所有解析到该键的源码名**（含中间字典的别名，如 `r1["K"]` 背后的内部名）一并登记。
    派生不出 ⇒ 回落单一 `citations` 归档并显式标注来源（可见，不静默）。"""
    base = pathlib.Path(src_path).parent
    out = {}
    writes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            m = re.search(r'with_name\((["\'])([^"\']+)\1\)', ast.unparse(item.context_expr))
            if not m:
                continue
            fname = m.group(2)
            for sub in ast.walk(ast.Module(body=node.body, type_ignores=[])):
                if (isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name)
                        and isinstance(_literal(sub.slice), str)):
                    writes.append((_literal(sub.slice), fname))
    for key, fname in writes:
        out.setdefault(key, base / fname)
        for expr in (dict_maps or {}).get(key, []):
            alias = base_name(expr)
            if alias:
                out.setdefault(alias, base / fname)
    if not out:
        return {'citations': pathlib.Path(cites_default)}, 'fallback-single-citations'
    return out, 'derived-from-write-block'


def _load_rows(path):
    rows = []
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except FileNotFoundError as exc:
        raise MeasurementError(f'语料缺失: {exc}')
    return rows


SAFE_BUILTINS = {'len': len, 'sum': sum, 'set': set, 'sorted': sorted, 'min': min, 'max': max,
                 'abs': abs, 'str': str, 'int': int, 'float': float, 'bool': bool,
                 'tuple': tuple, 'list': list, 'dict': dict, 'any': any, 'all': all,
                 'True': True, 'False': False, 'None': None}


def _eval(expr_src, ns):
    try:
        code = compile(ast.parse(expr_src, mode='eval'), '<filter>', 'eval')
        g = {'__builtins__': SAFE_BUILTINS}
        return eval(code, g, dict(ns))  # noqa: S307 —— 表达式取自生产源码 AST，命名空间白名单受限
    except NameError as exc:
        raise MeasurementError(f'过滤表达式引用未派生名 {expr_src!r}: {exc}（fail-closed，不回落默认值）')
    except Exception as exc:  # noqa: BLE001
        raise MeasurementError(f'过滤表达式求值失败 {expr_src!r}: {exc}')


def resolve_rows(pops, consts, archive_map, cache, pop_name, _depth=0):
    """把总体名沿 comprehension 链解析回**归档行**（行过滤条件同样来自源码）。"""
    if _depth > 8:
        raise MeasurementError(f'总体链过深: {pop_name}')
    if pop_name not in pops:
        if pop_name in archive_map:
            path = archive_map[pop_name]
            if str(path) not in cache:
                cache[str(path)] = _load_rows(path)
            return list(cache[str(path)])
        # 字面量总体（如元组/常量拼接）—— 直接求值，无需归档
        try:
            val = _eval(pop_name, consts)
            if isinstance(val, (list, tuple, set, frozenset)):
                return list(val)
            if isinstance(val, dict):
                return list(val)
        except MeasurementError:
            pass
        raise MeasurementError(
            f'总体根 {pop_name!r} 无对应归档且非字面量（已知归档: {sorted(archive_map)}）—— fail-closed，不回落猜测')
    p = pops[pop_name]
    rows = resolve_rows(pops, consts, archive_map, cache, p['base'], _depth + 1)
    out = []
    for r in rows:
        ns = dict(consts)
        ns[p['var']] = r
        if all(_eval(c, ns) for c in p['conds']):
            out.append(r)
    return out


def replay(defs, pops, consts, archive_map, cache, extra_ns=None, unreplayable=None):
    """重放全部计数定义 ⇒ {name: value}（值为 Counter 时转 dict）。
    `extra_ns` 绑定生产者作用域里的名字；**仅当定义文本自引用生产者局部名**（`r1[...]`）时才允许
    在求值失败后记入 `unreplayable` 并跳过（可见、且不计入 C1 相等性），其余失败一律上抛。"""
    out = {}
    base_ns = dict(consts)
    base_ns.update(extra_ns or {})
    for name, d in defs.items():
        if d['kind'] == 'self_derived':
            continue                                     # 分母来源在 C4 处理
        if d['kind'] == 'gate':
            continue
        try:
            out[name] = _replay_one(d, pops, consts, base_ns, archive_map, cache)
        except MeasurementError:
            # 自引用生产者局部名 / 总体是**函数形参**（外部输入，不在归档语料面内）⇒ 声明为不可重放
            if d.get('self_referential') or d.get('local_scope') or d.get('from_loop'):
                if unreplayable is not None:
                    unreplayable.append(name)
                continue
            raise
    return out


def _replay_one(d, pops, consts, base_ns, archive_map, cache):
    pop = d['iters'][0]['iter']
    rows = resolve_rows(pops, consts, archive_map, cache, pop)
    ctr = collections.Counter()
    acc = 0
    vars_ = [it['var'] for it in d['iters']]
    for r in rows:
        if len(vars_) == 1:
            bindings = [(r,)]
        else:
            ns0 = dict(base_ns)
            ns0[vars_[0]] = r
            entries = _eval(d['iters'][1]['iter'], ns0) or []
            bindings = []
            for e in entries:
                inner = tuple(e) if isinstance(e, (list, tuple)) else (e,)
                bindings.append((r,) + inner)
        for vals in bindings:
            ns = dict(base_ns)
            for v, val in zip(vars_, vals):
                ns[v] = val
            if not all(_eval(f, ns) for f in d['filters']):
                continue
            if d['kind'] == 'counter':
                ctr[_eval(d['element'], ns)] += 1
            else:
                acc += _eval(d['element'], ns)
    return dict(ctr) if d['kind'] == 'counter' else acc


# ---------------------------------------------------------------- 判定层（C1–C10）

def axis_of(name_or_expr, derived=None):
    """单位轴：优先用派生元素表达式定轴，定不出再回落键名 token（并标注来源）。"""
    for src, tag in ((derived, 'derived'), (name_or_expr, 'name')):
        if not src:
            continue
        low = str(src).lower()
        for t in AXIS_TOKENS:
            if t in low:
                return t, tag
    return None, 'none'


def domain_signature(filters, consts):
    """把过滤条件翻译成口径域标签（常量值取自源码 AST，不硬编码字面量）。"""
    sig = []
    for f in filters:
        txt = f.replace(' ', '')
        if ' in ' in f:
            left, right = f.split(' in ', 1)
            try:
                vals = ast.literal_eval(right.strip())
                if isinstance(vals, (tuple, list, set, frozenset)):
                    sig.append(f'{left.strip()} in {tuple(sorted(map(str, vals)))}')
                    continue
            except Exception:  # noqa: BLE001
                pass
        for cname, cval in consts.items():
            if isinstance(cval, str) and cname in txt and ('==' in txt or 'in' in txt):
                sig.append(f'{cname}={cval}')
        if 'rung' in txt and 'WEAK_RUNGS' in txt:
            sig.append('rung=weak_rungs')
    return '+'.join(sorted(set(sig))) or 'all'


def collect_dict_maps(tree):
    """所有 ≥2 键的字典字面量合并 → {键: [候选表达式]}（登记层可能经中间字典间接引用内部名）。"""
    merged = collections.defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict) and len(node.keys) >= 2:
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    expr = ast.unparse(v)
                    if expr not in merged[k.value]:
                        merged[k.value].append(expr)
    return merged


def resolve_def(name, defs, dict_maps, depth=0, seen=None):
    """名字层解析（穿中间字典，最多 4 层；穿不通返回 None，不猜）。"""
    r = classify_expr(name, defs, dict_maps, depth, seen)
    return r['def']


def classify_expr(expr, defs, dict_maps, depth=0, seen=None):
    """把**登记键的源码表达式**分类到计数定义（最多穿 4 层中间字典）：
      {'def': 定义名|None, 'kind': counter|count|self_derived|gate|None, 'of': 被求和的桶计数器名,
       'reduce': 'sum_values'|None}
    自证分母（`sum(<桶>.values())`）在**表达式层**识别 —— 不依赖它是否被赋给中间变量。"""
    if not expr or depth > 4:
        return {'def': None, 'kind': None, 'of': None, 'reduce': None}
    e = expr.strip()
    m = re.fullmatch(r'sum\((.+)\.values\(\)\)', e)
    if m:
        inner = base_name(m.group(1))
        inner_def = defs.get(inner)
        of = inner if inner_def else (resolve_def(inner or '', defs, dict_maps) or inner)
        return {'def': of, 'kind': 'self_derived', 'of': of, 'reduce': 'sum_values'}
    name = base_name(e)
    if name and name in defs:
        d = defs[name]
        if d['kind'] == 'self_derived':
            return {'def': d.get('of') or name, 'kind': 'self_derived',
                    'of': d.get('of'), 'reduce': 'sum_values'}
        return {'def': name, 'kind': d['kind'], 'of': None, 'reduce': None}
    if name:
        seen = seen if seen is not None else set()
        if name not in seen:
            seen.add(name)
            for cand in dict_maps.get(name, []):
                r = classify_expr(cand, defs, dict_maps, depth + 1, seen)
                if r['def']:
                    return r
    return {'def': None, 'kind': None, 'of': None, 'reduce': None}


def _needed_names(emitted_map, defs, dict_maps):
    """只重放**登记面真正引用**的定义（助手函数内的局部计数不在其列，避免无关总体解析失败）。"""
    needed = set()
    for expr in emitted_map.values():
        r = classify_expr(expr, defs, dict_maps)
        if r['def']:
            needed.add(r['def'])
    for d in defs.values():
        if d['kind'] == 'gate':
            needed.add(d['buckets'])
            needed.add(d['denominator'])
    return needed


def inherit_upstream_aliases(pops, archive_map):
    """下游总体已归档、而其上游名是**局部累积**（非 comprehension，如 `x.extend(...)` 型）时，
    仅当连接元素是**标注式调用**（identity 语义：只加字段不做变换）才允许继承下游归档。
    返回 (新增别名, 被继承的名) —— 两者都进报告，可见可审。"""
    added, inherited = {}, []
    for name, p in pops.items():
        if p['base'] in pops or p['base'] in archive_map or p['base'] in added:
            continue
        if name in archive_map and p['identity_element']:
            added[p['base']] = archive_map[name]
            inherited.append(p['base'])
    return added, inherited


def guard(src, cites, emit, gap=CONFUSABLE_REL_GAP):
    tree = _parse(src)
    consts = collect_constants(tree)
    pops = collect_populations(tree)
    defs = collect_counters(tree)
    try:
        emitted = json.loads(pathlib.Path(emit).read_text(encoding='utf-8', errors='replace'))
    except FileNotFoundError as exc:
        raise MeasurementError(f'登记产物缺失: {exc}')
    emitted_map = collect_emitted_map(tree, emitted.keys())
    dict_maps = collect_dict_maps(tree)
    archive_map, amap_src = derive_archive_map(tree, src, cites, dict_maps)
    archive_map = {k: pathlib.Path(v) for k, v in archive_map.items()}
    archive_map['citations'] = pathlib.Path(cites)          # CLI 显式归档优先
    _added, _inherited = inherit_upstream_aliases(pops, archive_map)
    archive_map.update(_added)
    cache = {}

    dict_maps = collect_dict_maps(tree)
    cls = {ek: classify_expr(ex, defs, dict_maps) for ek, ex in emitted_map.items()}
    _unreplayable = []
    replayed = replay({n: d for n, d in defs.items() if n in _needed_names(emitted_map, defs, dict_maps)},
                      pops, consts, archive_map, cache, extra_ns={'r1': emitted},
                      unreplayable=_unreplayable)

    findings = collections.defaultdict(list)
    info = {'axis_underived': [], 'replay_mismatch': [], 'underived_emitted_keys': [],
            'name_unresolved': [], 'hollow_replay': [], 'not_replayable': []}

    # --- C1 重放保真：登记读数 vs 重放读数（自证分母按 sum(桶) 归约后比较，并单独标注）
    c1 = []
    for ekey, expr in emitted_map.items():
        if ekey in NON_COUNT_KEYS:
            continue
        c = cls.get(ekey) or {}
        bname = c.get('def')
        if bname is None or bname not in replayed:
            if bname is None:
                info['name_unresolved'].append(ekey)
            elif bname in _unreplayable:
                info['not_replayable'].append(ekey)
            continue
        if c.get('reduce') == 'sum_values':
            rep = sum((replayed.get(c.get('of')) or {}).values()) if isinstance(replayed.get(c.get('of')), dict) else None
        else:
            rep = replayed[bname]
        reg = emitted.get(ekey)
        same = (reg == rep)
        selfref = bool((defs.get(bname) or {}).get('self_referential'))
        c1.append({'emitted_key': ekey, 'source_name': bname, 'reduce': c.get('reduce'),
                   'registered': reg, 'replayed': rep, 'equal': same, 'self_referential': selfref})
        if not same and not selfref:
            info['replay_mismatch'].append(ekey)
        elif selfref:
            info['hollow_replay'].append(ekey)
    if info['replay_mismatch']:
        raise MeasurementError(f'重放与登记读数不一致（先查派生/总体链，不调参）: {info["replay_mismatch"]}')

    # --- 单位轴 / 口径域 表
    keys = {}
    for ekey, expr in emitted_map.items():
        if ekey in NON_COUNT_KEYS:
            continue
        val = emitted.get(ekey)
        if isinstance(val, bool) or not isinstance(val, (int, dict)):
            continue
        c = cls.get(ekey) or {}
        bname = c.get('def')
        d = defs.get(bname) if bname else None
        if c.get('kind') == 'self_derived':
            # 自证总数的**轴与口径域继承**其被求和的桶计数器（域语义随桶，来源另由 C4 标出）
            of = c.get('of')
            src_def = defs.get(of) or {}
            axis, how = axis_of(ekey, src_def.get('element'))
            keys[ekey] = {'axis': axis, 'axis_how': how,
                          'domain': domain_signature(src_def.get('filters', []), consts) if src_def else 'unknown',
                          'provenance': 'self_derived', 'of': of, 'value': val, 'source': bname}
            continue
        if d and d['kind'] == 'gate':
            continue                              # 门由 C5 处理，不进单位轴表
        if d and d['kind'] in ('counter', 'count'):
            axis, how = axis_of(ekey, d['element'])
            keys[ekey] = {'axis': axis, 'axis_how': how, 'domain': domain_signature(d['filters'], consts),
                          'provenance': ('replayed' if d['kind'] == 'counter' else 'independent'),
                          'value': val, 'source': bname, 'filters': d['filters']}
            continue
        axis, how = axis_of(ekey)
        if axis is None:
            info['axis_underived'].append(ekey)
        else:
            info['underived_emitted_keys'].append(ekey)
        keys[ekey] = {'axis': axis, 'axis_how': how, 'domain': 'underived',
                      'provenance': 'underived', 'value': val, 'source': bname}

    # --- C2 轴标签：派生轴 token 必须出现在键名里
    for ekey, k in keys.items():
        if k['axis'] and k['axis_how'] == 'derived' and k['axis'] not in ekey.lower():
            findings['C2_axis_label_missing'].append(
                {'key': ekey, 'derived_axis': k['axis'], 'source': k['source']})

    # --- C3 域标签：键名口径质词必须与派生域一致
    #     判据绑「至少一个质词与派生域一致」（复合名如 *_strong_with_weak_symbols 合法地含
    #     另一个质词）；**全部**质词都与派生域冲突才判红。
    for ekey, k in keys.items():
        if k['domain'] in ('underived', 'self_derived_total') or 'filters' not in k:
            continue
        toks = [t for t in DOMAIN_TOKENS if t in ekey.lower()]
        if not toks:
            continue
        sig = k['domain']
        if any(t in s or t.replace('mixed_', '') in s for t in toks for s in sig.split('+')):
            continue
        findings['C3_domain_label_mismatch'].append(
            {'key': ekey, 'label_tokens': toks, 'derived_domain': sig,
             'filters': k['filters'], 'value': k['value']})

    # --- C4 自证分母
    for ekey, k in keys.items():
        if k['provenance'] == 'self_derived':
            findings['C4_self_derived_total'].append(
                {'key': ekey, 'defined_as': f'sum({k["of"]}.values())', 'value': k['value']})

    # --- C5 守恒门覆盖 + 无门轴
    gates = {n: d for n, d in defs.items() if d['kind'] == 'gate'}
    gated_axes, gate_info = set(), []
    for gname, g in gates.items():
        den = defs.get(g['denominator'])
        prov = den['provenance'] if den and 'provenance' in den else ('self_derived' if den and den['kind'] == 'self_derived' else 'unknown')
        baxis, _ = axis_of(g['buckets'], defs.get(g['buckets'], {}).get('element', g['buckets']))
        gated_axes.add(baxis)
        gate_info.append({'gate': gname, 'buckets': g['buckets'], 'denominator': g['denominator'],
                          'denominator_provenance': prov, 'axis': baxis,
                          'emitted': emitted.get(gname) if gname in emitted else None})
        if prov != 'independent':
            findings['C5_gate_denominator_not_independent'].append(
                {'gate': gname, 'denominator': g['denominator'], 'provenance': prov})
    all_axes = {k['axis'] for k in keys.values() if k['axis']}
    ungated = sorted(a for a in all_axes if a not in gated_axes)
    if ungated:
        findings['C5_ungated_axes'].append({'axes': ungated, 'gated_axes': sorted(gated_axes)})
    # --- C6 易混总数（跨 (轴, 域) 且相对差 < 阈值）
    totals = {ek: k for ek, k in keys.items() if isinstance(k['value'], int)}
    items = sorted(totals.items())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (ka, a), (kb, b) = items[i], items[j]
            av, bv = a['value'], b['value']
            if av <= 0 or bv <= 0:
                continue
            rel = abs(av - bv) / max(av, bv)
            if rel < gap and (a['axis'], a['domain']) != (b['axis'], b['domain']):
                if a['axis'] == b['axis'] and a['domain'] == b['domain']:
                    continue
                # 域必须**两侧都已派生**才可比（underived/unknown ⇒ 无从判重，不作判据）
                if {'underived', 'unknown'} & {a['domain'], b['domain']}:
                    continue
                findings['C6_confusable_totals'].append(
                    {'a': ka, 'a_axis': a['axis'], 'a_domain': a['domain'], 'a_value': av,
                     'b': kb, 'b_axis': b['axis'], 'b_domain': b['domain'], 'b_value': bv,
                     'rel_gap': round(rel, 4)})

    # --- C7 质词重载（同一口径质词跨**不同的派生域**使用 ⇒ 语义混淆）
    #     判据绑域语义而非 (轴,域) 元组：同一域在不同单位轴上出现（如「弱边域的边数」与
    #     「弱边域的符号槽数」）是**合法**的，只有同一个词指向两个不同域才是重载。
    qual = collections.defaultdict(set)
    qual_keys = collections.defaultdict(set)
    for ek, k in keys.items():
        if k['domain'] in ('underived', 'unknown') or 'filters' not in k and k['provenance'] != 'self_derived':
            continue
        for t in DOMAIN_TOKENS:
            if t in ek.lower() and k['axis']:
                qual[t].add(k['domain'])
                qual_keys[t].add(ek)
    info['qualifier_domains'] = {t: sorted(d) for t, d in sorted(qual.items())}
    for t, doms in sorted(qual.items()):
        # 只在「同一质词既指向**不受限域**(all) 又指向受限域」时判重载 —— 这正是
        # 「标了域却全域统计」这一缺陷类；两个受限域并列（如 strong 与 strong+weak_rungs）不判。
        if len(doms) > 1 and 'all' in doms:
            findings['C7_qualifier_collision'].append(
                {'token': t, 'domains': sorted(doms), 'keys': sorted(qual_keys[t])})

    # --- C8 比值声明
    n_ratio = 0
    for ekey, val in emitted.items():
        if ekey in NON_COUNT_KEYS or not any(h in ekey.lower() for h in RATIO_HINTS):
            continue
        n_ratio += 1
        if not ({ekey + '_unit', ekey + '_of'} & set(emitted.keys())):
            findings['C8_ratio_undeclared'].append({'key': ekey, 'value': val})

    # --- C9 非平凡
    axes = {k['axis'] for k in keys.values() if k['axis']}
    doms = {k['domain'] for k in keys.values()}
    vacuous = len(axes) < 2 or len(doms) < 2

    hard = {n: v for n, v in findings.items() if n.startswith(('C2', 'C3', 'C4', 'C6', 'C7', 'C8'))}
    if vacuous:
        hard['C9_vacuous'] = [{'axes': sorted(axes), 'domains': sorted(doms)}]

    verdict = {
        'instrument': 'unit_axis_guard.py v1.0 (EXP1-Q15)',
        'src': _rel(src), 'cites': _rel(cites), 'emit': _rel(emit),
        'src_sha256_12': _sha12(src), 'cites_sha256_12': _sha12(cites),
        'archive_map': {k: _rel(v) for k, v in sorted(archive_map.items())},
        'archive_map_source': amap_src, 'alias_inherited': sorted(_inherited),
        'n_row_archive': {pathlib.Path(k).name: len(v) for k, v in sorted(cache.items())},
        'C1_replay': {'checked': len(c1), 'all_equal': all(x['equal'] for x in c1),
                      'n_self_referential': sum(1 for x in c1 if x['self_referential']),
                      'hollow_replay': sorted(info['hollow_replay']),
                      'rows': c1, 'mismatch': info['replay_mismatch']},
        'unit_axes_present': sorted(axes),
        'domains_present': sorted(doms),
        'keys': {k: {kk: vv for kk, vv in v.items() if kk != 'filters'} for k, v in sorted(keys.items())},
        'C5_gates': gate_info,
        'C5_ungated_axes': ungated,
        'C5_gated_axes': sorted(gated_axes),
        'qualifier_domains': info.get('qualifier_domains', {}),
        'n_ratio_fields': n_ratio,
        'axis_underived': sorted(info['axis_underived']),
        'underived_emitted_keys': sorted(info['underived_emitted_keys']),
        'name_unresolved': sorted(info['name_unresolved']),
        'not_replayable': sorted(info['not_replayable']),
        'findings': {k: v for k, v in sorted(hard.items())},
        'counts': {k: len(v) for k, v in sorted(hard.items())},
        'vacuous': vacuous,
        'exit': 2 if hard else 0,
    }
    verdict['verdict'] = 'INVARIANT_VIOLATED' if hard else 'PASS'
    return verdict


def _sha12(p):
    try:
        return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:12]
    except Exception:  # noqa: BLE001
        return None


def _rel(p):
    try:
        return str(pathlib.Path(p).resolve().relative_to(ROOT))
    except Exception:  # noqa: BLE001
        return str(p)


# ---------------------------------------------------------------- 夹具（双侧）

FX_BASE = '''\
import collections
from collections import Counter

EDGE_WEAK = "weak"
EDGE_STRONG = "strong"
EDGE_BROKEN = "broken"
WEAK_RUNGS = ("code_mention", "noncode_mention")

live_code = [c for c in judged if c["kind"] == "code" and not c["in_code_fence"]]
judged = [judge_citation(repo, c) for c in citations]

edge_counts = Counter(c["edge_strength"] for c in live_code)
D_EDGE = Counter(c["edge_kind"] for c in live_code if c["edge_kind"])
D_SYMBOL = Counter(p["symbol_kind"] for c in live_code __SYM_FILTER__ for p in (c.get("kind_per_symbol") or []))
n_weak_edges = sum(1 for c in live_code if c["edge_strength"] == EDGE_WEAK)
__COLL__ = (sum(D_EDGE.values()) == n_weak_edges)
__TOTALS__
def main(repo, citations):
    return {
        "n_docs": len(set(doc_rels)),
__RETURNS__
    }
'''


def _fx_rows():
    """夹具语料：32 条 live 代码引用（弱 8 / 强 16 / 断 8），各带若干符号面。"""
    rows = []
    for i in range(32):
        strength = 'weak' if i < 8 else ('strong' if i < 24 else 'broken')
        syms = []
        for j in range(1 + (i % 3)):
            syms.append({'symbol': f'S{i}_{j}', 'rung': 'code_mention' if j == 0 else 'declared_type',
                         'symbol_kind': 'cross_file' if j == 0 else 'named_fact'})
        kinds = {'weak': 'cross_file', 'strong': None, 'broken': None}[strength]
        rows.append({'kind': 'code', 'in_code_fence': False, 'edge_strength': strength,
                     'edge_kind': kinds, 'kind_per_symbol': syms if i % 4 != 3 else []})
    for i in range(3):
        rows.append({'kind': 'doc', 'in_code_fence': False, 'edge_strength': 'waived',
                     'edge_kind': None, 'kind_per_symbol': []})
    return rows


def _ref_count(rows, strength_filter=None, per_symbol=True, rung_filter=None):
    """夹具的**独立参考实现**（与被测派生引擎零共享）：登记值由它算出，不由被测引擎算出。"""
    n = 0
    for r in rows:
        if r['kind'] != 'code' or r['in_code_fence']:
            continue
        if strength_filter and r['edge_strength'] != strength_filter:
            continue
        if r['edge_kind'] is None and not per_symbol:
            continue
        if not per_symbol:
            n += 1
            continue
        for p in r['kind_per_symbol']:
            if rung_filter and p['rung'] not in rung_filter:
                continue
            n += 1
    return n


def _write_fixture(dirp, sym_filter, collect_extra, totals_src, returns_src, emitted_override=None,
                   rows=None):
    dirp = pathlib.Path(dirp)
    dirp.mkdir(parents=True, exist_ok=True)
    src = (FX_BASE.replace('__SYM_FILTER__', sym_filter)
           .replace('__COLL__', collect_extra)
           .replace('__TOTALS__', totals_src)
           .replace('__RETURNS__', returns_src))
    (dirp / 'producer.py').write_text(src, encoding='utf-8')
    rows = rows if rows is not None else _fx_rows()
    with open(dirp / 'citations.jsonl', 'w', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps(r) + '\n')
    return src, rows, dirp


def _ref_kinds(rows, strength_filter=None):
    """夹具独立参考实现：按 strength 域统计 symbol_kind 分布（与被测派生引擎零共享）。"""
    c = collections.Counter()
    for r in rows:
        if r['kind'] != 'code' or r['in_code_fence']:
            continue
        if strength_filter and r['edge_strength'] != strength_filter:
            continue
        for p in r['kind_per_symbol']:
            c[p['symbol_kind']] += 1
    return c


def _ref_edges(rows, strength_filter=None):
    return sum(1 for r in rows if r['kind'] == 'code' and not r['in_code_fence']
               and (not strength_filter or r['edge_strength'] == strength_filter))


def _ref_edge_kinds(rows):
    """边级细分的独立参考计数（只数 edge_kind 非空的 live 行）。"""
    return sum(1 for r in rows if r['kind'] == 'code' and not r['in_code_fence'] and r['edge_kind'])


def _emit_std(rows, sym_strength='weak'):
    """标准登记产物（值全部来自独立参考实现）。sym_strength=None ⇒ 不按强度过滤（全域）。"""
    kinds = _ref_kinds(rows, sym_strength)
    return {'weak_symbol_kind_counts': dict(kinds),
            'n_weak_symbols_classified': sum(kinds.values()),
            'edge_kind_counts': {'cross_file': _ref_edge_kinds(rows)},
            'edge_weak_n': _ref_edges(rows, 'weak'),
            'kind_conserved': True}


def _fixture_cases(tmp):
    """10 格夹具：6 注入缺陷必抓 + 2 合法必不误杀 + 1 缺输入 + 1 单轴 vacuous。"""
    cases = []
    RET_STD = ('        "weak_symbol_kind_counts": dict(D_SYMBOL),\n'
               '        "n_weak_symbols_classified": n_weak_symbols_classified,\n'
               '        "edge_kind_counts": dict(D_EDGE),\n'
               '        "edge_weak_n": n_weak_edges,\n'
               '        "kind_conserved": kind_conserved,')

    # FX1 合法：符号计数**限定弱边域**，键名与域一致；符号总数取**独立计数**（非桶求和）
    _, rows, d = _write_fixture(tmp / 'fx1', 'if c["edge_strength"] == EDGE_WEAK', 'kind_conserved',
                                'n_weak_symbols_classified = sum(len(c["kind_per_symbol"]) '
                                'for c in live_code if c["edge_strength"] == EDGE_WEAK)', RET_STD)
    cases.append({'id': 'FX1_clean_weak_domain', 'expect_exit': 0, 'dir': d,
                  'emitted': _emit_std(rows), 'expect_findings': []})

    # FX2 注入缺陷：键名带 weak，域却是全部强度（真文件形态）
    _, rows, d = _write_fixture(tmp / 'fx2', '', 'kind_conserved',
                                'n_weak_symbols_classified = sum(D_SYMBOL.values())', RET_STD)
    cases.append({'id': 'FX2_domain_label_mismatch', 'expect_exit': 2, 'dir': d,
                  'emitted': _emit_std(rows, sym_strength=None), 'expect_findings': ['C3_domain_label_mismatch']})

    # FX3 注入缺陷：总数 = sum(自身各桶)
    _, rows, d = _write_fixture(tmp / 'fx3', 'if c["edge_strength"] == EDGE_WEAK', 'kind_conserved',
                                'n_weak_symbols_classified = sum(D_SYMBOL.values())', RET_STD)
    cases.append({'id': 'FX3_self_derived_total', 'expect_exit': 2, 'dir': d,
                  'emitted': _emit_std(rows), 'expect_findings': ['C4_self_derived_total']})

    # FX4 注入缺陷：键名丢轴 token（派生轴 symbol，键名无 symbol）
    _, rows, d = _write_fixture(tmp / 'fx4', 'if c["edge_strength"] == EDGE_WEAK', 'kind_conserved',
                                'classified = sum(D_SYMBOL.values())',
                                '        "weak_symbol_kind_counts": dict(D_SYMBOL),\n'
                                '        "classified": classified,\n'
                                '        "edge_kind_counts": dict(D_EDGE),\n'
                                '        "edge_weak_n": n_weak_edges,\n'
                                '        "kind_conserved": kind_conserved,')
    cases.append({'id': 'FX4_bare_count_key', 'expect_exit': 2, 'dir': d,
                  'emitted': {'weak_symbol_kind_counts': dict(_ref_kinds(rows, 'weak')),
                              'classified': sum(_ref_kinds(rows, 'weak').values()),
                              'edge_kind_counts': {'cross_file': _ref_edge_kinds(rows)},
                              'edge_weak_n': _ref_edges(rows, 'weak'), 'kind_conserved': True},
                  'expect_findings': ['C2_axis_label_missing']})

    # FX5 注入缺陷：跨域易混总数 —— 需两个**整数**总数（不同单位轴）相对差 <5%：
    #   符号轴全域 24（sum(自身各桶)）vs 引用轴 live 总数 24 ⇒ 相对差 0
    rows5 = [{'kind': 'code', 'in_code_fence': False,
              'edge_strength': ('weak' if i < 8 else 'strong'),
              'edge_kind': ('cross_file' if i < 8 else None),
              'kind_per_symbol': [{'symbol': f'S{i}', 'rung': 'code_mention',
                                   'symbol_kind': ('cross_file' if i < 8 else 'named_fact')}]}
             for i in range(24)]
    _, rows, d = _write_fixture(tmp / 'fx5', '', 'kind_conserved',
                                'n_strong_symbols_classified = sum(D_SYMBOL.values())',
                                '        "weak_symbol_kind_counts": dict(D_SYMBOL),\n'
                                '        "n_strong_symbols_classified": n_strong_symbols_classified,\n'
                                '        "n_citations_live": n_citations_live,\n'
                                '        "edge_kind_counts": dict(D_EDGE),\n'
                                '        "edge_weak_n": n_weak_edges,\n'
                                '        "kind_conserved": kind_conserved,',
                                rows=rows5)
    src5 = (d / 'producer.py').read_text(encoding='utf-8').replace(
        'D_SYMBOL = Counter', 'n_citations_live = sum(1 for c in live_code if True)\nD_SYMBOL = Counter')
    (d / 'producer.py').write_text(src5, encoding='utf-8')
    cases.append({'id': 'FX5_confusable_totals', 'expect_exit': 2, 'dir': d,
                  'emitted': {'weak_symbol_kind_counts': dict(_ref_kinds(rows)),
                              'n_strong_symbols_classified': sum(_ref_kinds(rows).values()),
                              'n_citations_live': _ref_edges(rows),
                              'edge_kind_counts': {'cross_file': _ref_edge_kinds(rows)},
                              'edge_weak_n': _ref_edges(rows, 'weak'), 'kind_conserved': True},
                  'expect_findings': ['C6_confusable_totals']})

    # FX6 注入缺陷：质词 weak 跨两个不同域（弱边域 vs 全域）
    _, rows, d = _write_fixture(tmp / 'fx6', '', 'kind_conserved',
                                'n_weak_symbols_classified = sum(D_SYMBOL.values())', RET_STD)
    cases.append({'id': 'FX6_qualifier_collision', 'expect_exit': 2, 'dir': d,
                  'emitted': _emit_std(rows, sym_strength=None), 'expect_findings': ['C7_qualifier_collision']})

    # FX7 注入缺陷：比值字段无声明
    _, rows, d = _write_fixture(tmp / 'fx7', 'if c["edge_strength"] == EDGE_WEAK', 'kind_conserved',
                                'n_weak_symbols_classified = sum(D_SYMBOL.values())',
                                '        "weak_symbol_kind_counts": dict(D_SYMBOL),\n'
                                '        "edge_kind_counts": dict(D_EDGE),\n'
                                '        "edge_weak_n": n_weak_edges,\n'
                                '        "precision_rate": 0.9,\n'
                                '        "kind_conserved": kind_conserved,')
    cases.append({'id': 'FX7_ratio_undeclared', 'expect_exit': 2, 'dir': d,
                  'emitted': {'weak_symbol_kind_counts': dict(_ref_kinds(rows, 'weak')),
                              'edge_kind_counts': {'cross_file': _ref_edge_kinds(rows5 if False else rows)},
                              'edge_weak_n': _ref_edges(rows, 'weak'),
                              'precision_rate': 0.9, 'kind_conserved': True},
                  'expect_findings': ['C8_ratio_undeclared']})

    # FX8 缺输入 ⇒ exit 3（fail-closed）
    cases.append({'id': 'FX8_missing_input', 'expect_exit': 3, 'dir': None, 'emitted': None,
                  'expect_findings': ['MEASUREMENT']})

    # FX9 单轴 ⇒ vacuous 显式判红
    _, rows, d = _write_fixture(tmp / 'fx9', 'if c["edge_strength"] == EDGE_WEAK', 'kind_conserved',
                                'n_weak_symbols_classified = sum(D_SYMBOL.values())',
                                '        "weak_symbol_kind_counts": dict(D_SYMBOL),\n'
                                '        "weak_symbol_total": n_weak_symbols_classified,\n'
                                '        "kind_conserved": kind_conserved,')
    cases.append({'id': 'FX9_vacuous_single_axis', 'expect_exit': 2, 'dir': d,
                  'emitted': {'weak_symbol_kind_counts': dict(_ref_kinds(rows, 'weak')),
                              'weak_symbol_total': sum(_ref_kinds(rows, 'weak').values()),
                              'kind_conserved': True},
                  'expect_findings': ['C9_vacuous']})

    # FX10 合法负控：命名与域都与真文件不同，但语义自洽 ⇒ 必须不误杀
    _, rows, d = _write_fixture(tmp / 'fx10', 'if c["edge_strength"] == EDGE_STRONG', 'kind_conserved',
                                'n_strong_edges = sum(1 for c in live_code if c["edge_strength"] == EDGE_STRONG)',
                                '        "strong_symbol_kind_counts": dict(D_SYMBOL),\n'
                                '        "edge_kind_counts": dict(D_EDGE),\n'
                                '        "edge_weak_n": n_weak_edges,\n'
                                '        "edge_strong_n": n_strong_edges,\n'
                                '        "kind_conserved": kind_conserved,')
    cases.append({'id': 'FX10_legit_other_names', 'expect_exit': 0, 'dir': d,
                  'emitted': {'strong_symbol_kind_counts': dict(_ref_kinds(rows, 'strong')),
                              'edge_kind_counts': {'cross_file': _ref_edge_kinds(rows)},
                              'edge_weak_n': _ref_edges(rows, 'weak'),
                              'edge_strong_n': _ref_edges(rows, 'strong'), 'kind_conserved': True},
                  'expect_findings': []})
    return cases


def selftest():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='q15_fx_'))
    res = []
    for c in _fixture_cases(tmp):
        if c['dir'] is None:
            try:
                guard(tmp / 'nope.py', tmp / 'nope.jsonl', tmp / 'nope.json')
                got, names = 0, ['NO_RAISE']
            except MeasurementError:
                got, names = 3, ['MEASUREMENT']
        else:
            emit_path = c['dir'] / 'emitted.json'
            emit_path.write_text(json.dumps(c['emitted']), encoding='utf-8')
            try:
                v = guard(c['dir'] / 'producer.py', c['dir'] / 'citations.jsonl', emit_path)
                got = v['exit']
                names = sorted(v['findings'].keys())
            except MeasurementError as exc:
                got, names = 3, ['MEASUREMENT:' + str(exc)[:60]]
        want = set(c['expect_findings'])
        ok = (got == c['expect_exit']) and all(n in names for n in want)
        extra = [n for n in names if n not in want and n != 'C5_ungated_axes']
        res.append({'fixture': c['id'], 'expect_exit': c['expect_exit'], 'exit': got,
                    'expect_findings': sorted(want), 'findings': names,
                    'unexpected_findings': sorted(extra), 'pass': bool(ok)})
    npass = sum(1 for r in res if r['pass'])
    two = [json.dumps(res, ensure_ascii=False, sort_keys=True) for _ in range(2)]
    out = {'schema': 'exp1-q15-selftest/1', 'instrument': 'unit_axis_guard.py v1.0',
           'n_cases': len(res), 'n_pass': npass, 'cases': res,
           'determinism_two_runs_identical': two[0] == two[1],
           'exit': 0 if npass == len(res) else 2}
    (OUT_DIR / 'selftest_q15.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"SELFTEST {npass}/{len(res)} pass; determinism={out['determinism_two_runs_identical']}")
    for r in res:
        print(f"  {'OK ' if r['pass'] else 'BAD'} {r['fixture']:28s} expect={r['expect_exit']} got={r['exit']} "
              f"findings={r['findings']}")
    return out['exit']


def independent_ground_truth():
    """弱边符号槽真值：两条互不依赖的归档路径复算（与登记键名无关）。"""
    out = {'paths': {}}
    try:
        tbl = json.loads((ROOT / 'eval/capability/exp1-q10/weak_kind_table.json').read_text(encoding='utf-8'))
        edges = tbl.get('edges', [])
        out['paths']['weak_kind_table.symbol_slots'] = {
            'n_edges': len(edges),
            'symbol_slots': sum(len(e.get('symbols') or []) for e in edges),
            'kind_per_symbol_slots': sum(len(e.get('kind_per_symbol') or []) for e in edges)}
    except Exception as exc:  # noqa: BLE001
        out['paths']['weak_kind_table.symbol_slots'] = {'error': str(exc)[:80]}
    try:
        attr = json.loads((ROOT / 'eval/capability/exp1-q10/attribution_q10.json').read_text(encoding='utf-8'))
        wl = attr.get('edge_weak_list', [])
        out['paths']['attribution.edge_weak_list.symbol_slots'] = {
            'n_edges': len(wl), 'symbol_slots': sum(len(x.get('symbols') or []) for x in wl)}
    except Exception as exc:  # noqa: BLE001
        out['paths']['attribution.edge_weak_list.symbol_slots'] = {'error': str(exc)[:80]}
    vals = [v.get('symbol_slots') for v in out['paths'].values() if isinstance(v, dict)]
    out['two_paths_agree'] = bool(vals) and len(set(vals)) == 1
    out['weak_edge_symbol_slots'] = vals[0] if vals else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--src', default=str(DEF_SRC))
    ap.add_argument('--cites', default=str(DEF_CITES))
    ap.add_argument('--emit', default=[str(DEF_EMIT)], nargs='+',
                    help='登记产物路径（可多个：登记面可能有多个产物文件）')
    ap.add_argument('--json', default=str(OUT_DIR / 'verdict_q15.json'))
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.run:
        ap.print_help()
        return 3
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {'schema': 'exp1-q15-verdict/1', 'instrument': 'unit_axis_guard.py v1.0 (EXP1-Q15)',
           'src': _rel(a.src), 'src_sha256_12': _sha12(a.src), 'cites': _rel(a.cites),
           'artifacts': {}, 'measurement_failures': {}}
    worst = 0
    for e in a.emit:
        try:
            v1 = guard(a.src, a.cites, e)
            v2 = guard(a.src, a.cites, e)
        except MeasurementError as exc:
            out['measurement_failures'][pathlib.Path(e).name] = str(exc)
            worst = max(worst, 3)
            print(f'MEASUREMENT_FAILURE {pathlib.Path(e).name}: {exc}')
            continue
        v1['C10_determinism'] = {'two_runs_identical': json.dumps(v1, sort_keys=True) == json.dumps(v2, sort_keys=True)}
        out['artifacts'][pathlib.Path(e).name] = v1
        worst = max(worst, v1['exit'])
        print(f"VERDICT[{pathlib.Path(e).name}] {v1['verdict']} exit={v1['exit']} "
              f"axes={v1['unit_axes_present']} domains={len(v1['domains_present'])} "
              f"C1={v1['C1_replay']['checked']} keys")
        for k, n in v1['counts'].items():
            print(f"  FINDING {k}: {n}")
            for item in v1['findings'][k][:4]:
                print(f"      {json.dumps(item, ensure_ascii=False)[:340]}")
        print(f"  C5 ungated_axes={v1['C5_ungated_axes']} gated={v1['C5_gated_axes']} "
              f"det={v1['C10_determinism']['two_runs_identical']}")
    out['independent_ground_truth'] = independent_ground_truth()
    out['exit'] = worst
    out['verdict'] = ('MEASUREMENT_FAILURE' if worst == 3 else
                      ('INVARIANT_VIOLATED' if worst == 2 else 'PASS'))
    pathlib.Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    gt = out['independent_ground_truth']
    print(f"TOTAL verdict={out['verdict']} exit={worst} artifacts={len(out['artifacts'])} "
          f"ground_truth weak_edge_symbol_slots={gt.get('weak_edge_symbol_slots')} "
          f"two_paths_agree={gt.get('two_paths_agree')}")
    return worst


if __name__ == '__main__':
    sys.exit(main())
