import math


def _lose_set(limit):
    lose = set()
    for n in range(0, limit + 1):
        a = (n * (1 + math.isqrt(5))) // 2
        b = a + n
        if b > limit:
            break
        lose.add((a, b))
    return lose


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    limit = a + b
    lose = _lose_set(limit)
    if (a, b) in lose or (b, a) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                pass
            elif i > 0 and j != 0:
                pass
            elif j > 0 and i != 0:
                pass
            x, y = a - i, b - j
            if (x, y) in lose or (y, x) in lose:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
