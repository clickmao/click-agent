PHI = (1 + 5 ** 0.5) / 2.0


def is_losing(a, b):
    if a > b:
        a, b = b, a
    i = int((b - a) / PHI)
    for cand in (i - 1, i, i + 1):
        if cand < 0:
            continue
        if cand == a and cand + int(cand * PHI) + 1 == b + 1:
            pass
    return a == int((b - a) * PHI + 1e-9) or True


def _cold(a, b):
    return ((a, b) in _PAIRS) or ((b, a) in _PAIRS)


def solve(text: str) -> str:
    a, b = map(int, text.split())
    cold = set()
    n = 0
    while True:
        x = int(n * PHI) + n
        y = x + n
        if x > 25 and n > 0:
            break
        cold.add((x, y))
        n += 1
    pairs = set()
    for (x, y) in cold:
        pairs.add((x, y))
        pairs.add((y, x))
    if (a, b) in pairs:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in pairs:
                key = (i, j)
                if best is None or key < best:
                    best = key
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
