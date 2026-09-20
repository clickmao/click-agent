import math


def _losing_positions(lim):
    losing = set()
    phi = (1 + math.sqrt(5)) / 2
    d = 0
    while True:
        xi = int(d * phi + 1e-9)
        if xi > lim:
            break
        losing.add((xi, xi + d))
        losing.add((xi + d, xi))
        d += 1
    return losing


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])
    losing = _losing_positions(max(a, b))
    if (a, b) in losing:
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in losing:
                return "WIN %d %d" % (i, j)
    return "LOSE"
