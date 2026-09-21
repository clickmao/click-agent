def solve(text: str) -> str:
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])

    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        return x == int(d * ((1 + 5 ** 0.5) / 2))

    if losing(a, b):
        return 'LOSE'
    n = max(a, b) + 1
    for i in range(0, n):
        for j in range(0, n):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and i <= a and j <= b:
                if losing(a - i, b - j):
                    return 'WIN %d %d' % (i, j)
    return 'LOSE'
