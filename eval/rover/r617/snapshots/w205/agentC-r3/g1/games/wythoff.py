N = 25


def _pairs():
    cold = set()
    used = set()
    x = 0
    while True:
        a = x * 2 + 1
        b = a + x
        if b > N:
            break
        cold.add((a, b))
        cold.add((b, a))
        used.add(a)
        used.add(b)
        x += 1
    return cold


_COLD = _pairs()


def solve(text):
    a, b = map(int, text.split())
    if (a, b) in _COLD:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ra, rb = a - i, b - j
            if (ra, rb) not in _COLD:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            cand = (i, j)
            if best is None or cand < best:
                best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
