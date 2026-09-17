"""Wythoff 博弈: 判断必败点或给出字典序最小的必胜着法。"""


def _is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    # 必败点满足 a = floor(phi * n), b = a + n
    # floor(phi*n) = (isqrt(5*n*n) + n)//2
    from math import isqrt
    n = b - a
    return a == (isqrt(5 * n * n) + n) // 2


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    if _is_losing(a, b):
        return "LOSE"

    # 枚举所有合法着法, 选 (i, j) 字典序最小且留给对手必败态
    best = None
    # (i) 从第一堆取 i
    for i in range(1, a + 1):
        if _is_losing(a - i, b):
            best = (i, 0)
            break
    # (i) 从第二堆取 j
    if best is None or (0, 1) < best:
        for j in range(1, b + 1):
            if _is_losing(a, b - j):
                if best is None or (0, j) < best:
                    best = (0, j)
                break
    # (ii) 两堆同时取 t
    for t in range(1, min(a, b) + 1):
        if _is_losing(a - t, b - t):
            if best is None or (t, t) < best:
                best = (t, t)
            break

    return "WIN " + str(best[0]) + " " + str(best[1])
