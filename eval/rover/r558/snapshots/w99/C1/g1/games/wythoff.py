from math import isqrt


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    # Wythoff cold positions: (floor(n*phi), floor(n*phi^2)) for n >= 0,
    # computed exactly with floor(k*sqrt(5)) via integer square root.
    cold = set()
    for n in range(0, 64):
        x = (n + isqrt(5 * n * n)) // 2
        y = x + n
        cold.add((x, y))
        cold.add((y, x))

    if (a, b) in cold:
        return 'LOSE'

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i and j and i != j:
                continue
            if (a - i, b - j) in cold:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
