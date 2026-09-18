def _lose(a, b):
    lo, hi = (a, b) if a <= b else (b, a)
    d = hi - lo
    x = int(d * 1.6180339887498949)
    for cand in (x - 1, x, x + 1):
        if cand < 0:
            continue
        if cand == lo and cand + d == hi:
            return True
    return False


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if _lose(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _lose(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
