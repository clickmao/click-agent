def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    # P-positions of Wythoff's game are (A_n, B_n) with
    #   A_n = floor(n * phi),  B_n = A_n + n,
    # taken in both orders.  Verified by the standard Beatty-sequence proof.
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    ppos = set()
    n = 0
    while True:
        x = int(n * phi)
        y = x + n
        n += 1
        if x > max(a, b) and y > max(a, b):
            break
        ppos.add((x, y))
        ppos.add((y, x))

    if (a, b) in ppos:
        return 'LOSE'

    # Legal moves are: change one coordinate, or subtract the same amount
    # from both.  Pick the lexicographically smallest (i, j) landing on a
    # P-position.
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and (a - i, b - j) in ppos:
                if best is None or (i, j) < best:
                    best = (i, j)

    i, j = best
    return 'WIN %d %d' % (i, j)
