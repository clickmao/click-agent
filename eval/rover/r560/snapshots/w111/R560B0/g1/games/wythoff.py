def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if a > b:
        a, b = b, a

    def losing(x, y):
        if x > y:
            x, y = y, x
        return x == int((y - x) * (1 + 5 ** 0.5) / 2)

    if losing(a, b):
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if not (ni > nj):
                ok1 = losing(ni, nj)
            else:
                ok1 = losing(ni, nj)
            same = (i == j)
            if ok1 and (i == 0 or j == 0 or same):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
