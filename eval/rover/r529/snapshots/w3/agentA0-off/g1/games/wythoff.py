"""Wythoff 博弈必败点判定。

输入格式:
    一行两个整数 a b (1<=a<=25, 1<=b<=25), 两堆石子颗数。

玩法: 每次可选
    (i)  从任意一堆取走任意正数目的石子, 或
    (ii) 从两堆同时取走相同正数目的石子。
取走最后一颗者胜。

输出:
    先手必败 -> 一行 "LOSE"
    否则     -> 一行 "WIN i j"
        i,j>=0 且不同时为 0; 从第一堆取 i 颗、第二堆取 j 颗; (i,j) 按字典序最小。

判据: (x,y) 为必败点 <=> 无序对等于 (a_n, b_n), 其中
    a_n = floor(n*phi), b_n = a_n + n, phi = (1+sqrt5)/2
用纯整数实现 floor(n*phi), 避免浮点误差。
"""

import math


def _beatty_a(n):
    """精确计算 a_n = floor(n * phi) = (n + floor(n*sqrt5)) // 2。"""
    fn = math.isqrt(5 * n * n)          # floor(n*sqrt5)
    return (n + fn) // 2


def _losing(x, y):
    """位置 (x,y) 是否为必败点。"""
    if x > y:
        x, y = y, x
    n = 0
    while True:
        a = _beatty_a(n)
        if a > x:
            return False
        if a == x and a + n == y:
            return True
        n += 1


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    if _losing(a, b):
        return "LOSE"

    # 枚举全部合法着法, 取字典序最小 (i, j)。
    best = None
    for i in range(1, a + 1):                 # 只从第一堆取
        if _losing(a - i, b):
            best = (i, 0)
            break
    if best is None:
        for j in range(1, b + 1):             # 只从第二堆取
            if _losing(a, b - j):
                best = (0, j)
                break
    if best is None:
        for t in range(1, min(a, b) + 1):     # 两堆同取
            if _losing(a - t, b - t):
                best = (t, t)
                break
    i, j = best
    return "WIN {} {}".format(i, j)
