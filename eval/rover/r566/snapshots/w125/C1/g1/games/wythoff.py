import math


def _cold(x: int, y: int) -> bool:
    if x > y:
        x, y = y, x
    d = abs(y - x)
    return x == (d + math.isqrt(5 * d * d)) // 2


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if _cold(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _cold(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
