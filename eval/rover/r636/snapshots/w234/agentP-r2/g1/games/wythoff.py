def _cold(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    q = int(d * ((5 ** 0.5 + 1) / 2))
    while q * ((5 ** 0.5 + 1) / 2) < d - 1:
        q += 1
    return (a, b) == (q, q + d)


def solve(text):
    a, b = map(int, text.split())
    if _cold(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _cold(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
