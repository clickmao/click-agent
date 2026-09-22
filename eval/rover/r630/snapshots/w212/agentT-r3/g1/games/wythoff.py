def _is_lose(x: int, y: int) -> bool:
    if x > y:
        x, y = y, x
    d = y - x
    return x == int(d * (1 + 5 ** 0.5) / 2)


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 and j > 0) or (j == 0 and i > 0) or (i > 0 and i == j):
                if _is_lose(a - i, b - j):
                    cands.append((i, j))
    if not cands:
        return 'LOSE'
    i, j = min(cands)
    return 'WIN ' + str(i) + ' ' + str(j)
