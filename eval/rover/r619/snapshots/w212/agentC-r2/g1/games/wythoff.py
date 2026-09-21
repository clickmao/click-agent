"""Wythoff's game: losing positions and lexicographically least winning move."""

from math import isqrt


def _losing_set(limit: int):
    losing = set()
    n = 0
    while True:
        x = (n * (1 + isqrt(5))) // 2
        if x > limit:
            break
        y = x + n
        if y > limit:
            break
        if (x, y) not in losing:
            losing.add((x, y))
            losing.add((y, x))
        n += 1
    return losing


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    losing = _losing_set(25)
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0:
                if i != j or i > a or j > b:
                    continue
            ra, rb = a - i, b - j
            if ra < 0 or rb < 0:
                continue
            if (ra, rb) in losing:
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
