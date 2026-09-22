"""Wythoff 博弈: 判定必败点, 否则给出字典序最小的必胜着法。"""


def _lose(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    d = b - a
    # Beatty 序列: a == floor(d*phi)
    phi = (1 + 5 ** 0.5) / 2
    return a == int(d * phi)


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _lose(a, b):
        return 'LOSE'
    # 枚举全部合法着法, 取字典序最小 (先比 i 再比 j)
    best = None
    # (i) 从任意一堆取任意正整数
    for i in range(1, a + 1):
        if _lose(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(1, b + 1):
        if _lose(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # (ii) 两堆同时取相同正整数
    for t in range(1, min(a, b) + 1):
        if _lose(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
