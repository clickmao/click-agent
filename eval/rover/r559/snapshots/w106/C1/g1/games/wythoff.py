def solve(text: str) -> str:
    a, b = map(int, text.split())

    def losing(x, y):
        lo, hi = min(x, y), max(x, y)
        d = hi - lo
        return lo == int(d * (1 + 5 ** 0.5) / 2)

    if losing(a, b):
        return "LOSE"

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if (i > 0) ^ (j > 0):
                if losing(ni, nj):
                    return "WIN %d %d" % (i, j)
            elif i > 0 and i == j:
                if losing(ni, nj):
                    return "WIN %d %d" % (i, j)
    return "LOSE"
