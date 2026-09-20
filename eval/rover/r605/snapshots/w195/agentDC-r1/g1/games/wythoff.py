def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    MAX = max(a, b)
    lose = set()
    for n in range(0, MAX + 1):
        p, q = (n * (1 + 5 ** 0.5) // 2), 0
        p = int(n * (1 + 5 ** 0.5) / 2)
        q = p + n
        if p > MAX:
            break
        lose.add((p, q))
        lose.add((q, p))
    if (a, b) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
