def solve(text: str) -> str:
    a, b = map(int, text.split())
    phi = (1 + 5 ** 0.5) / 2

    def is_losing(x, y):
        lo, hi = min(x, y), max(x, y)
        k = hi - lo
        if k < 0:
            return False
        # losing pair k is (floor(k*phi), floor(k*phi)+k)
        return int(k * phi + 1e-9) == lo

    if is_losing(a, b):
        return 'LOSE'

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
