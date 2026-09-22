def _losing_pairs(limit: int):
    used = set()
    pairs = set()
    n = 0
    while True:
        x = n
        while x in used:
            x += 1
        y = x + n
        if x > limit and y > limit:
            break
        if y <= limit:
            pairs.add((x, y))
            pairs.add((y, x))
        used.add(x)
        used.add(y)
        n += 1
    return pairs


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    lose = _losing_pairs(25)
    if (a, b) in lose:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in lose:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return "WIN " + str(best[0]) + " " + str(best[1])
