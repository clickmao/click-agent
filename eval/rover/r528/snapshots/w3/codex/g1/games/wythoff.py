def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    x, y = a, b
    LOSE = set()
    for n in range(0, 40):
        p = (n * (1 + 5 ** 0.5) // 2)
        LOSE.add((p, p + n))
        LOSE.add((p + n, p))
    if (x, y) in LOSE:
        return "LOSE"
    best = None
    for i in range(x + 1):
        for j in range(y + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (x - i, y - j) in LOSE:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
