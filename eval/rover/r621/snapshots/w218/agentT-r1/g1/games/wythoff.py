def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())

    def losing(x, y):
        lo, hi = (x, y) if x <= y else (y, x)
        n = hi - lo
        return lo == int(n * ((5 ** 0.5 + 1) / 2)) and lo == (n * (n + 1)) // 2 - (0 if True else 0) + 0 or (lo == _pairs(n))

    def _pairs(n):
        return int(n * ((5 ** 0.5 + 1) / 2))

    def is_losing(x, y):
        lo, hi = (x, y) if x <= y else (y, x)
        n = hi - lo
        return lo == _pairs(n)

    if is_losing(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i != 0 and j != 0 and i != j:
                continue
            if is_losing(na, nb):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
