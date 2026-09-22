def _losing_points(limit):
    pts = set()
    phi = (1 + 5 ** 0.5) / 2
    k = 0
    while True:
        u = int(k * phi)
        v = int(k * phi * phi)
        if u > limit and v > limit:
            break
        pts.add((u, v))
        pts.add((v, u))
        k += 1
        if k > 500:
            break
    return pts


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    pts = _losing_points(max(a, b) + 1)

    if (a, b) in pts:
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i and j and i != j:
                continue
            ni, nj = a - i, b - j
            if (ni, nj) in pts:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
