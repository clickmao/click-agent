import math


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'


def _is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    if a == 0:
        return b == 0
    return math.floor((b - a) * (1 + 5 ** 0.5) / 2) == a
