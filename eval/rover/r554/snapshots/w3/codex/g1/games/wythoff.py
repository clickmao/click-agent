from math import floor, sqrt

PHI = (1.0 + sqrt(5.0)) / 2.0


def _is_losing(p: int, q: int) -> bool:
    if p > q:
        p, q = q, p
    d = q - p
    return floor(d * PHI) == p and floor(d * PHI * PHI) == q


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    if _is_losing(a, b):
        return 'LOSE'

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if _is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
