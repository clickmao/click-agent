def _is_lose(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    import math
    ia = (d * (1 + math.sqrt(5)) / 2)
    return a == int(ia)


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if _is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _is_lose(na, nb):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
