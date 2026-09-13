# -*- coding: utf-8 -*-
"""G3/G5 闸门判定件判别力机检 (R395 固化两个真缺陷)。

真缺陷 1 (空心闸门): `train_adapter.py` 原文 `g["G5"] = True` —— 恒真, 确定性从未被检查。
真缺陷 2 (口径分叉): 文档 §5 的 G3 = "延迟 ≤15% ∧ RSS ≤15%", 代码 = "算力占比 <5%"。
判据 (零语言特性, 只看机制):
  ① 确定输入 → 判定器必须全过; **注入非确定性/状态污染 → 必须判不过** (判别力);
     分辨率边界 (**实测**, 不夸大仪器能力): 位级判据 ①② 抓任意量级漂移; ③ 是**秩级**仪器 ——
     1e-6 量级漂移**不改变** top-50 秩 (实测 Stateful 的 ranks 仍判过), 它只抓"会改 KPI 的
     秩级不稳定"; 故 ③ 另配一枚**会改秩**的注入样例 (Negated) 证明它非空心。
  ② 阈值唯一权威: 文档 §5 的 G3 三阈值 == 代码常量 (防漂移, 且语义词必须同时在场);
  ③ G3 每个子判据都有"过/不过"两侧构造样例 (防只写一侧的假断言)。
"""
import os, sys, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bge_lib as L
import train_adapter as T

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dim, r = 16, 8
mean = [0.0] * dim
V = [[1.0 if i == j else 0.0 for j in range(dim)] for i in range(r)]
ad = L.Adapter(mean, V, [1.0] * r, alpha=0.5)
# 夹具须**非退化**: 每条查询的金标准 = 对应语料块本身 (秩天然为 1) 且金标准**各不相同**。
# 反例 (实测): 6 条查询共用同一金标准 + 结构化工整语料 → 秩向量对注入不敏感, 会得出
# "秩判据空心"的**假结论** (夹具退化, 不是仪器空心)。
cv = [[math.sin(i * 0.1 + j) + 0.01 * j for j in range(dim)] for i in range(20)]
qv = [list(cv[i]) for i in range(6)]
cids = ["c%d" % i for i in range(len(cv))]
golds = ["c%d" % i for i in range(len(qv))]
_, ranks = L.recall_metrics([ad.encode(v) for v in cv], golds,
                            [ad.encode(v, True) for v in qv], cids)

# ① 判别力: 确定输入全过
det = T.determinism_checks(ad, cv, qv, golds, cids, ranks)
assert all(v is True for v in det.values()), "确定输入应全过, 实得 %r" % (det,)
print("OK ① 确定输入全过:", det)


class Stateful(L.Adapter):                      # 编码器污染自身状态 (真缺陷形态)
    def encode(self, x, query_side=False):
        self.mean[0] += 1e-6
        return L.Adapter.encode(self, x, query_side)


class Nondet(L.Adapter):                        # 真非确定性
    def encode(self, x, query_side=False):
        y = L.Adapter.encode(self, x, query_side)
        return [v + random.random() * 1e-9 for v in y]


for cls, tag in ((Stateful, "状态污染"), (Nondet, "非确定性")):
    bad = cls(list(mean), V, [1.0] * r, alpha=0.5)
    d = T.determinism_checks(bad, cv, qv, golds, cids, ranks)
    assert d["encode_repeat"] is False, "%s: encode_repeat 未判不过 %r" % (tag, d)
    assert d["negative_control"] is True, "%s: 负控失效 %r" % (tag, d)
    print("OK ② 负控抓住 %s:" % tag, d)
assert T.determinism_checks(Stateful(list(mean), V, [1.0] * r), cv, qv, golds, cids,
                            ranks)["order_invariant"] is False, "状态污染未被顺序判据抓住"


class ShiftedQuery(L.Adapter):
    """会**改秩**的注入: 证明 ③ 秩判据有判别力。

    注入设计也被两个错例修正过 (都记在此, 防后人重踩):
      ① `Negated` (整体取负) 对排序是**恒等变换** —— dot(-q,-c)=dot(q,c), 相似度矩阵不变;
      ② 只改查询侧零几个分量 → 夹具下仍不改秩。
    真正有效的注入: 查询侧分量**循环移位 1** —— 确定性 (①② 仍过) 但改变与语料块的相似度排序。
    """

    def encode(self, x, query_side=False):
        y = L.Adapter.encode(self, x, query_side)
        return ([y[-1]] + y[:-1]) if query_side else y


_inj = ShiftedQuery(list(mean), V, [1.0] * r, alpha=0.5)
_, rk_inj = L.recall_metrics([_inj.encode(v) for v in cv], golds,
                             [_inj.encode(v, True) for v in qv], cids)
dn = T.determinism_checks(_inj, cv, qv, golds, cids, ranks)
print("     基准秩 %r → 注入秩 %r" % (ranks, rk_inj))
assert rk_inj != ranks, "注入未改秩, 该注入无效 (夹具/注入问题)"
assert dn["ranks_reproducible"] is False, "秩级注入未被 ③ 抓住 (③ 空心): %r" % (dn,)
assert dn["encode_repeat"] is True and dn["order_invariant"] is True, ("注入必须是确定性的, "
                                                                     "否则测的不是 ③: %r" % (dn,))
print("OK ②b 秩级注入被 ③ 抓住 (③ 非空心):", dn)
# 分辨率边界固化: 1e-6 漂移**不应**被判为秩级不稳定 (否则是把仪器能力吹大)
assert T.determinism_checks(Stateful(list(mean), V, [1.0] * r, alpha=0.5), cv, qv, golds,
                            cids, ranks)["ranks_reproducible"] is True, "秩判据分辨率超出实测"""


# ③ 阈值唯一权威: 文档 §5 G3 行 == 代码常量, 且语义词在场
doc = io = None
import io as _io
p = os.path.join(REPO, "docs/plans/v0.22.0-exp7-bge-idle-training-loop.md")
rows = [l for l in _io.open(p, encoding="utf-8").read().splitlines() if l.startswith("| G3")]
assert len(rows) == 1, rows
line = rows[0]
assert line.count("15%") == 2 and "5%" in line, "文档 G3 阈值与常量不一致: %s" % line
for w in ("算力", "延迟", "内存"):
    assert w in line, "文档 G3 缺失语义维度 %s: %s" % (w, line)
assert (T.MAC_BUDGET, T.LAT_BUDGET, T.MEM_BUDGET) == (0.05, 0.15, 0.15)
print("OK ③ 文档 §5 与代码同阈值同语义:", line.strip()[:80])

# ④ G3 三子判据两侧样例
DIM_REAL = 512                    # 真实嵌入维 (夹具 dim=16 只为提速, 不得用于算力判据 —— 实测坑)
assert (2 * DIM_REAL * 64) / (24_000_000 * 2) <= T.MAC_BUDGET            # 实际采用档 r=64
assert (2 * DIM_REAL * 4096) / (24_000_000 * 2) > T.MAC_BUDGET, "算力负控失效"
mbytes = os.path.getsize(L.MODEL)
small = L.Adapter([0.0] * 512, [[1.0] * 512] * 512, [1.0] * 512, alpha=0.5,
                  W=[0.0] * (512 * 512))
assert T.adapter_bytes(small, 512) / mbytes <= T.MEM_BUDGET, T.adapter_bytes(small, 512) / mbytes
big = L.Adapter([0.0] * 1024, [[1.0] * 1024] * 1024, [1.0] * 1024, alpha=0.5,
                W=[0.0] * (1024 * 1024))
assert T.adapter_bytes(big, 1024) / mbytes > T.MEM_BUDGET, "内存负控失效"
import inspect
_src = inspect.getsource(T.measure_forward_ms)
_body = _src.split('"""')[2] if _src.count('"""') >= 2 else _src    # 剥掉 docstring 再看调用
assert "L.embed(" in _body and "embed_cached(" not in _body, \
    "前向测量必须**绕开缓存** (embed_cached 命中返回 0.0 ms → 分母变 0 的假判据)"
print("OK ④ G3 三子判据两侧样例 + 前向测量绕缓存机检")

# ⑤ G1 双判据 (R404 修的第三个真缺陷): 常数注册 + 配对检验数值对账 + **直接取源码右值**两侧样例
assert (T.G1_ALPHA, T.G1_MIN_GAIN_QUERIES) == (0.05, 6), \
    ("G1 常量漂移", T.G1_ALPHA, T.G1_MIN_GAIN_QUERIES)
for _bc, _want in [((15, 2), 0.0023), ((12, 0), 0.0005), ((2, 2), 1.0), ((3, 0), 0.25),
                   ((5, 0), 0.0625), ((6, 0), 0.03125), ((0, 0), 1.0)]:
    _got = T.mcnemar_exact(*_bc)
    assert abs(_got - _want) < 5e-5, "mcnemar_exact%s=%.6f 期望 %.4f" % (_bc, _got, _want)
_PLAN = os.path.join(REPO, "docs", "plans", "v0.22.0-exp7-bge-idle-training-loop.md")
assert os.path.isfile(_PLAN), _PLAN
_rows1 = [l for l in open(_PLAN, encoding="utf-8").read().splitlines() if l.startswith("| G1")]
assert len(_rows1) == 1 and "McNemar" in _rows1[0] and "6" in _rows1[0] and "0.05" in _rows1[0], \
    ("文档 G1 行与代码不一致", _rows1)
import ast, inspect
_src1 = inspect.getsource(T)
_node1 = next(n for n in ast.walk(ast.parse(_src1)) if isinstance(n, ast.Assign)
              and isinstance(n.targets[0], ast.Subscript)
              and getattr(n.targets[0].slice, "value", None) == "G1")
_expr1 = ast.get_source_segment(_src1, _node1.value)
assert all(k in _expr1 for k in ("G1_MIN_GAIN_QUERIES", "G1_ALPHA", "mcnemar_exact")), _expr1


def _g1(b, c):
    ns = {"__builtins__": {}, "gd": {"G1_detail": {"net": b - c}},
          "G1_MIN_GAIN_QUERIES": T.G1_MIN_GAIN_QUERIES, "G1_ALPHA": T.G1_ALPHA,
          "mcnemar_exact": T.mcnemar_exact, "_b": b, "_c": c}
    return eval(compile(ast.Expression(ast.parse("(" + _expr1 + ")", mode="eval").body), "<g1>", "eval"), ns)


assert _g1(15, 2) is True, "G1 漏判真增益 (融合线 15:2, p=0.0023)"
assert _g1(3, 0) is False, "G1 放行噪声 (+3 条 —— 旧式 2.5pt 阈值正是放行它)"
assert _g1(6, 0) is True, "G1 误杀边界真增益 (+6 条, 最小 p=0.03125)"
assert _g1(5, 0) is False, "G1 放行 +5 条 (最小 p=0.0625 > 0.05)"
assert _g1(9, 9) is False, "G1 放行净增 0"
print("OK ⑤ G1 配对判据: 常数(6, 0.05) + mcnemar 数值冻结 + 两侧样例(+3 拒 / +5 拒 / +6 收 / 15:2 收)")
print("OK: 闸门判定件判别力机检 全部通过")
