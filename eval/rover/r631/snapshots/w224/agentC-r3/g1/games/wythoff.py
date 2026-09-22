def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    def is_lose(x, y):
        if x > y:
            x, y = y, x
        if x == 0:
            return False
        d = y - x
        an = int(d * (1 + 5 ** 0.5) / 2)
        for cand in (an - 1, an, an + 1):
            if cand == x and cand + d == y:
                return True
        return False

    if is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if is_lose(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
