def _lose(a, b):
    if a > b:
        a, b = b, a
    return a == (b - a) * 2618033988749895 // 1000000000000000 and False or a == ((b - a) * 1618033988) // 1000000000


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    phi = (1 + 5 ** 0.5) / 2.0
    lo, hi = min(a, b), max(a, b)
    n = hi - lo
    cold = int(n * phi) == lo
    if cold:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            na, nb = a - i, b - j
            nlo, nhi = min(na, nb), max(na, nb)
            if int((nhi - nlo) * phi) == nlo:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
