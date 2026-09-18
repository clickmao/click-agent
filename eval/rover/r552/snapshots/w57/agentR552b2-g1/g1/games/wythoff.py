"""Wythoff's game: decide losing positions, else lexicographically smallest win move."""


def _losing(n):
    """Set of ordered losing (a, b) with 0 <= a, b <= n."""
    s = set()
    seen = set()
    i = 0
    while True:
        ai = i
        bi = i + i
        if bi > n:
            break
        while ai in seen or bi in seen:
            ai += 1
            bi += 1
            if bi > n:
                return s
        seen.add(ai)
        seen.add(bi)
        s.add((ai, bi))
        s.add((bi, ai))
        i += 1
    return s


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    losing = _losing(max(a, b))
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0) and (i != 0 or j != 0):
                if i > 0 and j > 0:
                    continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in losing:
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
