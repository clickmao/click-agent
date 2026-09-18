def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    def losing(x, y):
        if x > y:
            x, y = y, x
        # Wythoff P-positions: y - x = d, x = floor(d * phi)
        d = y - x
        return x == int(d * ((1 + 5 ** 0.5) / 2))

    if losing(a, b):
        return "LOSE"

    found = None
    best = None
    for i in range(0, a + 1):
        # single pile (first pile only), j = 0
        if i > 0 and losing(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
        # single pile (second pile only), i = 0
    for j in range(0, b + 1):
        if j > 0 and losing(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # equal amounts from both piles
    for t in range(1, min(a, b) + 1):
        if losing(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    return "WIN %d %d" % best
