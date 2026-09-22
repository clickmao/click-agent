"""Wythoff 博弈: 必败点判定; 必胜时给出字典序最小的着法 (i, j)。

stdin 规格: 一行两个整数 a b。
"""


def _is_lose(a: int, b: int) -> bool:
    """精确判定 (a, b) 是否为必败点 (先排序成 a <= b)。"""
    if a > b:
        a, b = b, a
    # 第 m 个必败点为 (floor(m*phi), floor(m*phi)+m)
    phi = 1.6180339887498949
    m = int(b - a)
    # 精确计算 floor(m*phi) 用整数, 避开浮点误差
    u = (m * 16180339887498949) // 10000000000000000
    while (u + 1) * 10000000000000000 <= m * 16180339887498949:
        u += 1
    while u * 10000000000000000 > m * 16180339887498949:
        u -= 1
    return a == u and b == u + m


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    if _is_lose(a, b):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _is_lose(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)

    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
