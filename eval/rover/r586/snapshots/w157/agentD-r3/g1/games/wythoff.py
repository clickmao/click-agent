"""Wythoff 博弈：判定必败点或输出字典序最小的必胜着法。"""


def solve(text: str) -> str:
    toks = text.split()
    a, b = int(toks[0]), int(toks[1])
    # 必败点 (lo, hi) 满足 lo = floor(n*phi), hi = lo + n
    PHI = (1 + 5 ** 0.5) / 2
    maxv = max(a, b)
    n = 0
    while True:
        lo = int(n * PHI + 1e-9)
        hi = lo + n
        if hi > maxv + 1:
            break
        if (a == lo and b == hi) or (a == hi and b == lo):
            return 'LOSE'
        n += 1
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            legal = False
            if j == 0 or i == 0:
                legal = True
            if i == j:
                legal = True
            if not legal:
                continue
            na, nb = a - i, b - j
            if _is_losing(na, nb):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])


def _is_losing(a, b):
    if a == 0 and b == 0:
        return True
    lo, hi = (a, b) if a <= b else (b, a)
    PHI = (1 + 5 ** 0.5) / 2
    n = 0
    while True:
        x = int(n * PHI + 1e-9)
        y = x + n
        if y > hi + 1:
            return False
        if lo == x and hi == y:
            return True
        n += 1
