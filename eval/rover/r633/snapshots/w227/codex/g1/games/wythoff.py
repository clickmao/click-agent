def _cold_positions(limit):
    """生成 Wythoff 博弈的必败点 (0,0), (1,2), (3,5), ..."""
    positions = set()
    n = 0
    while True:
        a = int(n * (1 + 5 ** 0.5) / 2)
        b = a + n
        if a > limit:
            break
        positions.add((a, b))
        if b <= limit:
            positions.add((b, a))
        if n == 0:
            positions.add((0, 0))
        n += 1
    return positions


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    cold = _cold_positions(limit + 2)

    if (a, b) in cold:
        return 'LOSE'

    best = None
    for i in range(1, a + 1):
        cand = (i, 0)
        if (a - i, b) in cold and (best is None or cand < best):
            best = cand
    for j in range(1, b + 1):
        cand = (0, j)
        if (a, b - j) in cold and (best is None or cand < best):
            best = cand
    for t in range(1, min(a, b) + 1):
        cand = (t, t)
        if (a - t, b - t) in cold and (best is None or cand < best):
            best = cand

    return 'WIN %d %d' % best
