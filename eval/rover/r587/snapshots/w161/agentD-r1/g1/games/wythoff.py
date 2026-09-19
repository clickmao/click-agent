"""Wythoff's game: lose-position test and lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    lo, hi = min(a, b), max(a, b)
    # Beatty / golden ratio characterization of P-positions.
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    t = int((hi - lo) * phi)
    ok = False
    for c in (t - 1, t, t + 1):
        if c >= 0:
            x = c
            y = c + (hi - lo)
            if x == lo and y == hi:
                ok = True
                break
    if ok:
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            na, nb = a - i, b - j
            lo2, hi2 = min(na, nb), max(na, nb)
            t2 = int((hi2 - lo2) * phi)
            q = False
            for c in (t2 - 1, t2, t2 + 1):
                if c >= 0 and c == lo2 and c + (hi2 - lo2) == hi2:
                    q = True
                    break
            if q:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
