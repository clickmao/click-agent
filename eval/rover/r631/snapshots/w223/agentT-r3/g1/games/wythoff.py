def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    losing = set()
    i = 0
    while True:
        p = (i * (1 + 5 ** 0.5) / 2.0)
        pi = int(p)
        if p - pi >= 1:
            pi += 1
        q = pi + i
        if pi > 25 and q > 25:
            break
        losing.add((pi, q))
        losing.add((q, pi))
        i += 1
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i2 in range(0, a + 1):
        for j2 in range(0, b + 1):
            if i2 == 0 and j2 == 0:
                continue
            if i2 != 0 and j2 != 0 and i2 != j2:
                continue
            if (a - i2, b - j2) in losing:
                if best is None or (i2, j2) < best:
                    best = (i2, j2)
    return 'WIN %d %d' % best
