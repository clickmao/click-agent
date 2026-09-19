def _losers(limit):
    losers = set()
    n = 1
    while True:
        a = n * 3 // 2
        while (a, a + n) in losers or (a + n, a) in losers or a <= 0:
            a += 1
        if a > limit:
            break
        losers.add((a, a + n))
        n += 1
    return losers


def solve(text):
    a, b = map(int, text.split())
    limit = max(a, b) + 2
    # Grundy-free representation: losing positions are (floor(phi*n), floor(phi*phi*n))
    losers = set()
    n = 1
    while True:
        x = int(n * (1 + 5 ** 0.5) / 2)
        y = x + n
        if x > 25 or y > 25:
            break
        losers.add((x, y))
        losers.add((y, x))
        n += 1
    if (a, b) in losers:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            # legal moves: from one pile only, or equal from both
            if (i > 0 and j == 0) or (i == 0 and j > 0) or (i == j):
                if (a - i, b - j) in losers:
                    if best is None:
                        best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
