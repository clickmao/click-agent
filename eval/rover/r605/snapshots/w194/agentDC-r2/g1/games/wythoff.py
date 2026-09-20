def solve(text: str) -> str:
    a, b = map(int, text.strip().split())
    lose = set()
    m = 0
    while True:
        x = int(m * 1.618033988749895) + m
        y = x + m
        if x > 25 or y > 25:
            break
        lose.add((x, y))
        lose.add((y, x))
        m += 1
    if (a, b) in lose:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in lose:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
