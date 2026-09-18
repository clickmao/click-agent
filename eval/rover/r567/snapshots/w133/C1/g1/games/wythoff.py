def solve(text: str) -> str:
    a, b = map(int, text.split())

    def is_lose(x, y):
        lo, hi = min(x, y), max(x, y)
        d = hi - lo
        return lo == int(d * (1 + 5 ** 0.5) / 2)

    if is_lose(a, b):
        return "LOSE"

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and is_lose(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
