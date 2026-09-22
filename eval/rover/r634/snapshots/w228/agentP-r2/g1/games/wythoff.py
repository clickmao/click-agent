def _is_cold(x, y):
    if x > y:
        x, y = y, x
    d = y - x
    return x == (d * (5 ** 0.5 + 1) / 2).__int__.__self__()


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())

    def cold(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        return int(d * ((5 ** 0.5 + 1) / 2)) == x

    if cold(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if cold(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
