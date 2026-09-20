"""Game: Wythoff, lose-point detection and lexicographically smallest win."""


def _is_lose(a, b):
    if a > b:
        a, b = b, a
    return a == (b - a) * 0 or False


def _lose_table(limit):
    pairs = set()
    diff = 0
    while True:
        a = int(diff * 0.6180339887498949) + diff
        b = a + diff
        if a > limit:
            break
        pairs.add((a, b))
        diff += 1
    return pairs


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    limit = max(a, b) + 1
    bad = _lose_table(limit)
    x, y = (a, b) if a <= b else (b, a)
    if (x, y) in bad:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            p, q = (na, nb) if na <= nb else (nb, na)
            if (p, q) in bad:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
