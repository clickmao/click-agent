def _cold(a, b):
    if a > b:
        a, b = b, a
    for n in range(0, 26):
        if (a, b) == (n, n + n):
            return True
    return False


def solve(text: str) -> str:
    a, b = map(int, text.split())
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _cold(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
