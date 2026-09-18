def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    def is_losing(x, y):
        d = abs(y - x)
        lo = (d * (1 + 5 ** 0.5) / 2.0)
        m = int(lo + 1e-9)
        for mm in (m - 1, m, m + 1):
            if mm < 0:
                continue
            if (mm, mm + d) == (min(x, y), max(x, y)):
                return True
        return False
    if is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0) or (i == j):
                if is_losing(a - i, b - j):
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
    return 'WIN %d %d' % best
