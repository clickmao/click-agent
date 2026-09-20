def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if a > b:
        a, b = b, a
    lose = set()
    p, q = 0, 0
    while p <= 25:
        lose.add((p, q))
        p, q = q + 1, p + q + 2
    if (a, b) in lose:
        return 'LOSE'
    x, y = a, b
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            r, s = a - i, b - j
            if r > s:
                r, s = s, r
            if (r, s) in lose:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
