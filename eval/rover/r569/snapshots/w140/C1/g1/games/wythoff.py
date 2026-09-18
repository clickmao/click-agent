PHI = (1 + 5 ** 0.5) / 2


def _is_cold(x: int, y: int) -> bool:
    if x > y:
        x, y = y, x
    if x == 0 and y == 0:
        return True
    d = y - x
    cx = int(d * PHI + 1e-9)
    return cx == x and cx + d == y


def solve(text: str) -> str:
    a, b = (int(v) for v in text.split()[:2])

    if _is_cold(a, b):
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_cold(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
