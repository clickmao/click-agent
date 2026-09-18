def _lose(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    t = (d * (1 + 5 ** 0.5) / 2)
    # integer golden-ratio ratio pair: a = floor(d*phi), b = a+d
    import math
    aa = int(math.floor(d * (1 + 5 ** 0.5) / 2))
    return a == aa


def _lose_set(n):
    seen = set()
    lose = set()
    a = 0
    while a <= n:
        d = 0
        while a + d <= n:
            b = a + d
            if (a, b) not in seen:
                lose.add((a, b))
                break
            d += 1
        a += 1
    return lose


def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    is_lose = _lose(a, b)
    if is_lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            x, y = a - i, b - j
            if (min(x, y), max(x, y)) and _lose(x, y):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
