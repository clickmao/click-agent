"""Wythoff's game: cold positions, else lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    limit = max(a, b)

    cold = set()
    cold.add((0, 0))
    used = set([0])
    n = 1
    while True:
        m = n
        while m in used:
            m += 1
        an = m
        bn = m + n
        if an > limit and bn > limit:
            break
        used.add(an)
        used.add(bn)
        cold.add((an, bn))
        cold.add((bn, an))
        n += 1

    if (a, b) in cold:
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in cold:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % (best[0], best[1])
