def _lose_pairs(limit):
    pairs = set()
    x, y = 0, 0
    while True:
        a, b = x, y
        if a > limit and b > limit:
            break
        pairs.add((a, b))
        pairs.add((b, a))
        x += 1
        y += 2
    return pairs


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    limit = a if a > b else b
    pairs = _lose_pairs(limit)
    if (a, b) in pairs:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in pairs:
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
