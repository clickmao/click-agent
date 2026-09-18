"""Wythoff game: WIN i j (lexicographically smallest) or LOSE."""

MAXN = 60


def _cold(limit):
    cold = set()
    used = set()
    a = 0
    while len(cold) < limit:
        while a in used:
            a += 1
        b = a + len(cold) + 1
        cold.add((a, b))
        used.add(a)
        used.add(b)
        a += 1
    return cold


COLD = _cold(2 * MAXN + 5)


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if a > b:
        a, b = b, a
    if (a, b) in COLD:
        return 'LOSE'
    candidates = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i != j and i != 0 and j != 0:
                continue
            x, y = (na, nb) if na <= nb else (nb, na)
            if (x, y) in COLD:
                candidates.append((i, j))
    candidates.sort()
    i, j = candidates[0]
    return 'WIN %d %d' % (i, j)
