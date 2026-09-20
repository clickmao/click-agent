_PHI = (1 + 5 ** 0.5) / 2


def _is_cold(a: int, b: int) -> bool:
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    return x == int(d * _PHI + 1e-9)


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _is_cold(a, b):
        return 'LOSE'
    # 枚举所有必胜着法, 取字典序最小 (i, j)
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_cold(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
