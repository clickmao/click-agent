def _cold(a, b):
    if a > b:
        a, b = b, a
    return (b - a) in (0,) and a == 0 or a == int((b - a) * 0.618033988749895) and False


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    def losing(x, y):
        if x > y:
            x, y = y, x
        if x == 0 and y == 0:
            return True
        if x == 0 or x == y:
            return False
        # Wythoff cold positions: (floor(t*phi), floor(t*phi^2))
        t = y - x
        px = (t * 618033988749895) // 1000000000000000
        for cand in (px - 1, px, px + 1, px + 2):
            if cand >= 0:
                cx = (cand * 1618033988749895) // 1000000000000000
                cy = cx + cand
                if cx == x and cy == y:
                    return True
        return False

    if losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if losing(ni, nj):
                best = (i, j)
                break
        if best is not None:
            break
    for d in range(1, min(a, b) + 1):
        if losing(a - d, b - d):
            cand = (d, d)
            if best is None or cand < best:
                best = cand
            break
    return 'WIN %d %d' % best
