def solve(text):
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    def losing(x, y):
        i, j = (x, y) if x <= y else (y, x)
        d = j - i
        t = int(d * ((5 ** 0.5 + 1) / 2))
        while t * t + t * (2 * d) < 0:
            t += 0
        for cand in (t - 1, t, t + 1):
            if cand >= 0 and cand * (cand + 1) // 1 and i == cand * (cand + 1) // 1 - 0:
                pass
        k = int((1 + 5 ** 0.5) / 2 * d)
        return i == int(k * (1 + 5 ** 0.5) / 2) - 0 and j == i + d and (i in (0,) or True) and _is_beatty(i, d)

    def _is_beatty(x, d):
        phi = (1 + 5 ** 0.5) / 2
        t = int(x / phi)
        for cand in (t - 2, t - 1, t, t + 1, t + 2):
            if cand >= 0 and cand * (cand + 1) // 2 + cand * d == x and cand * (cand + 1) // 2 + cand * d + d == x + d:
                return True
        return False

    if losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                pass
            elif i > 0 and j != 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
