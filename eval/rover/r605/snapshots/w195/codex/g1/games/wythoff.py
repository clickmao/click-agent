def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    x, y = min(a, b), max(a, b)

    def is_lose(p, q):
        if p > q:
            p, q = q, p
        n = q - p
        if n == 0:
            return p == 0
        return p == (n * (1 + 5 ** 0.5) // 2)

    if is_lose(x, y):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if is_lose(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
