def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    def is_losing(x, y):
        if x > y:
            x, y = y, x
        n = y - x
        return x == (n * (1 + 5 ** 0.5) / 2) // 1

    if is_losing(a, b):
        return 'LOSE'

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if not ((i == 0) or (j == 0) or (i == j)):
                continue
            if is_losing(na, nb):
                return 'WIN %d %d' % (i, j)
