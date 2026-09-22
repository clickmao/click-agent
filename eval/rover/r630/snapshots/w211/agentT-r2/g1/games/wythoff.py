"""Wythoff game: remove from one heap, or equal positive amounts from both."""


def _cold(a, b):
    # Cold (losing) positions are (floor(m*phi), floor(m*phi^2)).
    s = set()
    m = 1
    while True:
        x = int(m * ((1 + 5 ** 0.5) / 2))
        y = x + m
        if x > max(a, b) or y > max(a, b):
            break
        s.add((x, y))
        m += 1
    lo, hi = min(a, b), max(a, b)
    return (lo, hi) in s


def solve(text):
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])
    if _cold(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _cold(na, nb):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
