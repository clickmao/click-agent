def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    LOSE = set()
    i = 0
    while True:
        p = (int(i * (1 + 5 ** 0.5) / 2), int(i * (3 + 5 ** 0.5) / 2))
        if p[0] > 25 and p[1] > 25:
            break
        LOSE.add(p)
        i += 1
    # exact check via direct set (careful: pairs must equal golden pairs)
    def is_lose(x, y):
        return (x, y) in LOSE or (y, x) in LOSE

    if is_lose(a, b):
        return "LOSE"

    # enumerate all winning moves, pick lexicographically smallest (i, j)
    best = None
    # (i) remove from one pile
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            same_both = (i == j)
            one_pile = (i == 0) or (j == 0)
            if not (same_both or one_pile):
                continue
            if is_lose(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
