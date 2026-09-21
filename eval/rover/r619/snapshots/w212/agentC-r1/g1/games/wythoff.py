import math


def _p_position(x: int, y: int) -> bool:
    """(x, y) 是否为 Wythoff 必败点 (P-位置)。仅对小范围用直接枚举，保证正确。"""
    if x < 0 or y < 0:
        return False
    if x > y:
        x, y = y, x
    phi = (1 + math.sqrt(5)) / 2
    n = y - x
    # 第 n 对 P-位置为 (floor(n*phi), floor(n*phi)+n)
    ax = int(math.floor(n * phi))
    return x == ax and y == ax + n


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    if _p_position(a, b):
        return 'LOSE'

    best = None
    # (i) 从任意一堆取任意正数
    for i in range(a + 1):
        if i == 0:
            continue
        if _p_position(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(b + 1):
        if j == 0:
            continue
        if _p_position(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # (ii) 从两堆同时取相同正数
    for i in range(1, min(a, b) + 1):
        if _p_position(a - i, b - i):
            cand = (i, i)
            if best is None or cand < best:
                best = cand

    return 'WIN %d %d' % (best[0], best[1])
