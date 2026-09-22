def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    from math import isqrt
    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        p = (isqrt(5 * d * d) + d) // 2
        return x == p
    if losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0) or (j == 0) or (i == j):
                if losing(a - i, b - j):
                    if best is None or (i, j) < best:
                        best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
