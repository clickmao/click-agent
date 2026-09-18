def solve(text: str) -> str:
    a, b = map(int, text.split())
    LOSE = set()
    t = 0
    while True:
        x = (t * (1 + 5 ** 0.5) / 2)
        p, q = int(x), int(x) + t
        if p > 25 or q > 25:
            break
        LOSE.add((p, q))
        LOSE.add((q, p))
        t += 1
    if (a, b) in LOSE:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in LOSE:
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
