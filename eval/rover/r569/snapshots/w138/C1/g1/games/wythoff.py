import math

PHI = (1 + 5 ** 0.5) / 2


def _is_losing(x, y):
    if x > y:
        x, y = y, x
    d = y - x
    px = int(math.floor(d * PHI + 1e-9))
    return x == px


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if _is_losing(a, b):
        return 'LOSE'

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            is_single = (i == 0) != (j == 0)
            is_equal_pair = i > 0 and j > 0 and i == j
            if not (is_single or is_equal_pair):
                continue
            if _is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
