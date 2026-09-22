"""Wythoff's game: detect losing positions; else the lexicographically smallest winning move."""


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    # Standard characterization of P-positions via the golden ratio.
    gr = (1.0 + 5.0 ** 0.5) / 2.0
    lo = min(a, b)
    hi = max(a, b)
    n = int(lo / gr) + 1
    cand = []
    for t in (n - 1, n, n + 1):
        if t < 0:
            continue
        p = int(t * gr)
        q = p + t
        cand.append((p, q))
        cand.append((q, p))
    if (lo, hi) in cand:
        return 'LOSE'

    # Enumerate candidate moves in lexicographic order of (i, j).
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            lo2, hi2 = min(na, nb), max(na, nb)
            t = int(lo2 / gr) + 1
            ok = False
            for u in (t - 1, t, t + 1):
                if u < 0:
                    continue
                p = int(u * gr)
                q = p + u
                if (lo2, hi2) == (p, q) or (lo2, hi2) == (q, p):
                    ok = True
                    break
            if ok:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
