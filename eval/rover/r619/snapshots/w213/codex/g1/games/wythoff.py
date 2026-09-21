def solve(text: str) -> str:
    a, b = map(int, text.split())

    # Beatty pairs: P_m = (floor(m*phi), floor(m*phi) + m)
    lose = set()
    m = 0
    while True:
        n = int(m * (1 + 5 ** 0.5) / 2)
        if n > 25:
            break
        if n + m > 25:
            m += 1
            continue
        lose.add((min(n, n + m), max(n, n + m)))
        m += 1

    lo, hi = min(a, b), max(a, b)
    if (lo, hi) in lose:
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            key = (min(a - i, b - j), max(a - i, b - j))
            if key in lose:
                if best is None or (i, j) < best:
                    best = (i, j)

    return 'WIN %d %d' % best
