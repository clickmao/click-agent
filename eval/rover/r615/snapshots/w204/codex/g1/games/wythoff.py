def solve(text: str) -> str:
    a, b = map(int, text.split())
    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        p = (1 + 5 ** 0.5) / 2
        return x == int(d * p)

    if losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if losing(a - i, b - j):
                best = (i, j)
                break
        if best:
            break
    return 'WIN %d %d' % best
