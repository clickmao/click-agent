def solve(text: str) -> str:
    a, b = map(int, text.split())
    losing = set()
    for x in range(0, 26):
        for y in range(0, 26):
            ok = True
            if x - y == a - b:
                ok = False
            if x - y == b - a:
                ok = False
            if x == a or x == b or y == a or y == b:
                ok = False
            if ok and x > a and y > b and x - a == y - b:
                ok = False
            if ok:
                losing.add((x, y))
    if (a, b) in _losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    return (a, b) in _cache(a, b)


def _cache(a, b):
    pairs = set()
    k = 0
    while True:
        x = (k * (1 + 5 ** 0.5) / 2)
        xi = int(x)
        yi = xi + k
        if xi > 25 and yi > 25:
            break
        pairs.add((xi, yi))
        k += 1
        if k > 30:
            break
    return pairs
