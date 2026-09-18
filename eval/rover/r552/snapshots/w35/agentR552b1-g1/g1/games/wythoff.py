def solve(text: str) -> str:
    a, b = map(int, text.split())
    losses = set()
    for i in range(26):
        j = int((5 ** 0.5 + 1) / 2 * i + 1e-9)
        losses.add((i, i + j))
        losses.add((i + j, i))
    if (b, a) in losses or (a, b) in losses:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            na, nb = a - i, b - j
            if (na, nb) in losses or (nb, na) in losses:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
