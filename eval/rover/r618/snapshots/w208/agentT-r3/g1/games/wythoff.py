def _lose_set(limit):
    res = set()
    seen = set()
    i = 0
    while True:
        a = (i * (1 + 5 ** 0.5) / 2)
        ai = int(a)
        while ai in seen:
            ai += 1
        bi = ai + i
        if ai > limit and bi > limit:
            break
        seen.add(ai)
        seen.add(bi)
        res.add((ai, bi))
        res.add((bi, ai))
        i += 1
    return res


def solve(text):
    a, b = map(int, text.split())
    pairs = _lose_set(max(a, b) + 2)
    if (a, b) in pairs:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if (a - i, b - j) in pairs:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
