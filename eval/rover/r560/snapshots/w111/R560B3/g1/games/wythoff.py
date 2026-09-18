def _cold(a, b):
    if a > b:
        a, b = b, a
    return a == int((b - a) * (1 + 5 ** 0.5) / 2)


def solve(text: str) -> str:
    a, b = (int(t) for t in text.split()[:2])
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _cold(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
