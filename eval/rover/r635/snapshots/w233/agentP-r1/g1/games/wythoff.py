"""Wythoff game: losing positions; else lexicographically smallest winning move."""

MAXV = 25


def _losing_set(limit):
    s = set()
    n = 0
    while True:
        x = int(n * (1 + 5 ** 0.5) / 2)
        y = x + n
        if x > limit and y > limit:
            break
        if x <= limit and y <= limit:
            s.add((x, y))
        n += 1
    return s


_LOSING = None


def solve(text: str) -> str:
    global _LOSING
    if _LOSING is None:
        _LOSING = _losing_set(MAXV)
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    parts = lines[0].split()
    a = int(parts[0])
    b = int(parts[1])
    if (min(a, b), max(a, b)) in _LOSING:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                na = a - i
                nb = b - j
                if (min(na, nb), max(na, nb)) in _LOSING:
                    best = (i, j)
                    break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
