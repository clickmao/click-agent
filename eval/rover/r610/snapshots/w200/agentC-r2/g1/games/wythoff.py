"""Wythoff 博弈: 必败/必胜判定与字典序最小的必胜着法。

必败点恰为 (floor(n*phi), floor(n*phi^2)), n >= 0 (Beatty 序列)。
"""

PHI = (1 + 5 ** 0.5) / 2

def _is_losing(x, y):
    if x > y:
        x, y = y, x
    n = y - x
    if n == 0:
        return x == 0
    a = int(n * PHI)
    for cand in (a - 1, a, a + 1):
        if cand < 0:
            continue
        p = int(cand * PHI)
        q = int(cand * PHI * PHI)
        if x == p and y == q:
            return True
    return False

def solve(text):
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    if _is_losing(a, b):
        return 'LOSE'
    best = None
    # (1) 只从第一堆取 i 颗
    for i in range(1, a + 1):
        if _is_losing(a - i, b):
            best = (i, 0)
            break
    # (2) 只从第二堆取 j 颗
    if best is None:
        for j in range(1, b + 1):
            if _is_losing(a, b - j):
                best = (0, j)
                break
    # (3) 从两堆同时取相同数目 i 颗
    if best is None:
        for i in range(1, min(a, b) + 1):
            if _is_losing(a - i, b - i):
                best = (i, i)
                break
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
