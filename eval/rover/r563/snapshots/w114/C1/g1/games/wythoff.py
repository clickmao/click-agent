import math


def _is_lose(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    x = int(math.floor(d * (1 + 5 ** 0.5) / 2))
    return x == a and x + d == b


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_lose(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
