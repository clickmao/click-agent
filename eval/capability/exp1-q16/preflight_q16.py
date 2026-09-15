"""Q16 预检（先于实现与运行）：派生「循环累加型计数」的外层绑定链。
不做任何判定，只把结构事实打印出来（外/内层 For 的 target 与 iter、累加目标、条件），
并回答：face_rungs 的 iters 若补上外层绑定，总体根能否落到归档语料面。"""
import ast, pathlib, json, sys

SRC = pathlib.Path('eval/capability/exp1-q10/probe_v260.py')
GUARD = pathlib.Path('eval/capability/exp1-q15/unit_axis_guard.py')

src = SRC.read_text(encoding='utf-8')
tree = ast.parse(src)

# ---- 父链（ast.walk 无父指针 ⇒ 自建）
parent = {}
for node in ast.walk(tree):
    for child in ast.iter_child_nodes(node):
        parent[id(child)] = node

def enclosing_fors(node):
    chain = []
    cur = parent.get(id(node))
    while cur is not None:
        if isinstance(cur, ast.For):
            chain.append(cur)
        cur = parent.get(id(cur))
    return list(reversed(chain))          # 外层在前

def for_head(f):
    tgt = f.target
    if isinstance(tgt, ast.Name):
        names = [tgt.id]
    elif isinstance(tgt, ast.Tuple):
        names = [ast.unparse(e) for e in tgt.elts]
    else:
        names = []
    return {'vars': names, 'iter': ast.unparse(f.iter)}

rows = []
for node in ast.walk(tree):
    if not isinstance(node, ast.AugAssign):
        continue
    t = node.target
    if not (isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and node.op.__class__ is ast.Add):
        continue
    chain = enclosing_fors(node)
    if not chain:
        continue
    inner = chain[-1]
    outer = chain[:-1]
    # 累加所在 For 体内条件
    conds = [ast.unparse(s.test) for s in inner.body if isinstance(s, ast.If)]
    rows.append({
        'line': node.lineno,
        'acc_name': t.value.id,
        'key_expr': ast.unparse(t.slice),
        'inner': for_head(inner),
        'outer_chain': [for_head(f) for f in outer],
        'conds': conds,
        'outer_vars_used_in_inner_iter': sorted(
            v for f in outer for v in for_head(f)['vars'] if v in ast.unparse(inner.iter)),
        'key_is_inner_var': ast.unparse(t.slice) in for_head(inner)['vars'],
    })

# ---- 现状仪器会把哪些 from_loop def 收成什么样
sys.path.insert(0, str(GUARD.parent))
import importlib.util
spec = importlib.util.spec_from_file_location('uag', GUARD)
uag = importlib.util.module_from_spec(spec); spec.loader.exec_module(uag)
defs = uag.collect_counters(tree)
pops = uag.collect_populations(tree)
from_loop = {n: d for n, d in defs.items() if d.get('from_loop')}

out = {
    'augassign_rows_total': len(rows),
    'rows': rows,
    'from_loop_defs_now': {n: {'iters': d['iters'], 'element': d['element'], 'filters': d['filters']}
                           for n, d in from_loop.items()},
    'pops_have_live_code': 'live_code' in pops,
    'live_code_pop': pops.get('live_code'),
    'pop_names': sorted(pops),
}
pathlib.Path('eval/capability/exp1-q16/preflight.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({k: v for k, v in out.items() if k != 'rows'}, ensure_ascii=False, indent=1)[:2000])
print('--- rows with outer chain ---')
for r in rows:
    print(json.dumps(r, ensure_ascii=False))
