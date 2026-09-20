def _losing(a: int, b: int) -> bool:
    x, y = (a, b) if a <= b else (b, a)
    t = y - x
    bx = int(t * (1 + 5 ** 0.5) / 2 + 1e-9)
    return x == bx and y == bx + t


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _losing(a, b):
        return 'LOSE'
    best = None
    # single-pile removals: (i, 0) with i >= 1, and (0, j) with j >= 1
    for i in range(1, a + 1):
        if _losing(a - i, b):
            best = (i, 0)
            break
    if best is None:
        for j in range(1, b + 1):
            if _losing(a, b - j):
                best = (0, j)
                break
    if best is None:
        # equal removals from both piles: i == j >= 1
        for i in range(1, min(a, b) + 1):
            if _losing(a - i, b - i):
                best = (i, i)
                break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
