# -*- coding: utf-8 -*-
"""岭回归"拟合空间 == 应用空间"回归机检 (真机缺陷固化: r@1=0.0 / median_rank=999)。

真缺陷: 拟合用 `_base` (未 λ 缩放), 应用时 W 乘在 `_base/λ^α` 上 → 输入空间不一致。
判据 (零语言特性, 只看机制): 在应用空间线性可分的映射, 拟合+应用同空间时必须高保真;
把 W 应用到**另一个空间**的输入必须显著变差 (反向控制, 防"空心断言")。
"""
import os, sys, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bge_lib as L
import train_adapter as T

r = 32
random.seed(20260913)
M = [[random.gauss(0, 1) if i == j else random.gauss(0, 0.25) for j in range(r)] for i in range(r)]
Q = [[random.gauss(0, 1) for _ in range(r)] for _ in range(160)]
P = [[sum(M[i][j] * q[j] for j in range(r)) for i in range(r)] for q in Q]


def cos(a, b):
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb + 1e-12)


W = T.solve_ridge(Q, P, r, 1e-9)

# ① 同空间: 拟合空间输入 → 高保真 (cos ≈ 1)
same = sum(cos(L.matvec(W, Q[i]), P[i]) for i in range(len(Q))) / len(Q)
print("同空间平均 cos: %.4f" % same)
assert same > 0.99, "拟合空间与应用空间一致时必须高保真, 实得 %.4f" % same

# ② 反向控制: 把 W 应用到**逐维 λ 缩放后**的输入 (真缺陷的错用方式) → 必须显著变差
lam_a = [1.0 + 0.5 * (i % 7) for i in range(r)]           # 模拟 λ^α 的逐维缩放 (量级 1~4)
Qscaled = [[v[i] / lam_a[i] for i in range(r)] for v in Q]
bad = sum(cos(L.matvec(W, Qscaled[i]), P[i]) for i in range(len(Q))) / len(Q)
print("异空间 (逐维缩放输入) 平均 cos: %.4f" % bad)
assert bad < same - 0.05, "反向控制失效: 跨空间应用竟然也好 (%.4f vs %.4f)" % (bad, same)

# ③ 生产接线: train_adapter 的拟合输入必须来自与 encode 相同的 λ 缩放空间
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "train_adapter.py"), encoding="utf-8").read()
assert "_apply_space" in src, "拟合侧未走 λ 缩放空间 (回归!)"
assert "Qr = [base_w._base(v) for v in tqv]" not in src, "旧的 `_base` 直拟合写法回来了 (回归!)"
assert "w = [zi / (self.lambdas[i] ** self.alpha)" in open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "bge_lib.py"), encoding="utf-8").read(), \
    "应用侧 λ 缩放写法变了 —— 两侧约定需重新对齐"

print("OK: 拟合空间对齐机检 4/4 通过")
