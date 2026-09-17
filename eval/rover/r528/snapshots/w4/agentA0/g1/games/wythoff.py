"""Wythoff 博弈: 两堆石子, 可从任一堆取任意正数, 或从两堆同取相同正数。

取尽最后一颗者胜。输出: 必败 -> LOSE; 否则 WIN i j (字典序最小的必胜着法)。
必败点集合: 由公式 (floor(n*phi), floor(n*phi)+n) 生成, 且两坐标对称。
"""

import math

_PHI = (1 + math.sqrt(5)) / 2


def _is_losing(a, b):
    """判断 (a, b) 是否为必败点。"""
    lo, hi = min(a, b), max(a, b)
    n = hi - lo
    if n < 0:
        return False
    # 必败点满足 lo == floor(n*phi) 且 hi == lo + n
    if lo == int(math.floor(n * _PHI)):
        return True
    return False


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_losing(a, b):
        return 'LOSE'

    best = None  # (i, j) 字典序最小
    # 着法一: 从第一堆取 i, 第二堆不动 (i>=1)
    for i in range(1, a + 1):
        if _is_losing(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
            break
    # 着法二: 第一堆不动, 从第二堆取 j (j>=1)
    for j in range(1, b + 1):
        if _is_losing(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
            break
    # 着法三: 两堆同取 t
    for t in range(1, min(a, b) + 1):
        if _is_losing(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand
            break
    return 'WIN %d %d' % best
