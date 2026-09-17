"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。

必败点 (P-positions) 为 (floor(k*phi), floor(k*phi)+k) 及其交换,
phi = (1+sqrt(5))/2。
"""

import math


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    k = b - a
    return a == int(math.floor(k * (1 + math.sqrt(5)) / 2))


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _is_losing(a, b):
        return 'LOSE'

    best = None
    # 情形 (i): 只从一堆取
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 必须作用在某一堆（不能同时动两堆且数目不同）
            if i > 0 and j > 0:
                continue
            if _is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    # 情形 (ii): 从两堆取相同数目
    for t in range(1, min(a, b) + 1):
        if _is_losing(a - t, b - t):
            if best is None or (t, t) < best:
                best = (t, t)

    return 'WIN %d %d' % best
