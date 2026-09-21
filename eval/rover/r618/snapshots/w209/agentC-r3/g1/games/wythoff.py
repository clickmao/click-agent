def solve(text: str) -> str:
    a, b = map(int, text.split())

    def losing(x, y):
        if x > y:
            x, y = y, x
        return x == int((y - x) * (1 + 5 ** 0.5) / 2 + 1e-9)

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
