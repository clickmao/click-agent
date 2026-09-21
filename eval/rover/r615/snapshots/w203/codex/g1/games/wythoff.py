import math


def _losing(n):
    return (math.floor(n * (1 + 5 ** 0.5) / 2),
            math.floor(n * (3 + 5 ** 0.5) / 2))


def _losing_set(limit):
    positions = set()
    n = 0
    while True:
        x, y = _losing(n)
        if x > limit and y > limit:
            break
        positions.add((x, y))
        positions.add((y, x))
        n += 1
    return positions


_LOSING = _losing_set(400)


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    for i in range(a + 1):
        for j in range(b + 1):
            if (i, j) == (0, 0):
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            if (a - i, b - j) not in _LOSING:
                return "WIN %d %d" % (i, j)
    return "LOSE"
