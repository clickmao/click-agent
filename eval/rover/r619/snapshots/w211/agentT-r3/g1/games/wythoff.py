"""Wythoff game: detect a losing position or give the lexicographically smallest winning move."""
MAX = 25


def _losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    for k in range(0, MAX + 2):
        pk = int(k * (1 + 5 ** 0.5) / 2)
        qk = pk + k
        if pk > MAX or qk > MAX:
            break
        if (a, b) == (pk, qk) or (a, b) == (qk, pk):
            return True
    return False


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
