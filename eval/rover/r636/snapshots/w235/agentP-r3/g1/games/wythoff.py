"""Wythoff game: LOSE or WIN i j (lexicographically smallest move)."""


def _p_set(limit_a, limit_b):
    pset = set()
    z = 0
    while True:
        lo = int(z * (1 + 5 ** 0.5) / 2)
        hi = lo + z
        if lo > limit_a and hi > limit_b:
            break
        if lo <= limit_a and hi <= limit_b:
            pset.add((lo, hi))
        if z > 40:
            break
        z += 1
    return pset


def solve(text: str) -> str:
    a, b = map(int, text.split())
    pset = _p_set(max(a, b), max(a, b))
    if (a, b) in pset:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na == 0 and nb == 0:
                cand = (i, j)
            else:
                cand = (i, j) if (min(na, nb), max(na, nb)) in pset else None
            if cand is not None:
                best = cand
                break
        if best is not None:
            break
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
