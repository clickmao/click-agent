def _cold(limit):
    pairs = set()
    d = 0
    while True:
        a = int(d * (5 ** 0.5 + 1) / 2)
        if a + d > limit:
            break
        pairs.add((a, a + d))
        d += 1
    return pairs


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])
    cold = _cold(max(a, b))
    if (min(a, b), max(a, b)) in cold:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or (i > a) or (j > b):
                continue
            na, nb = a - i, b - j
            if (min(na, nb), max(na, nb)) in cold:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
