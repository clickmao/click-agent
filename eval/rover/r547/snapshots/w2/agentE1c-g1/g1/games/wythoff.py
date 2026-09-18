"""Wythoff game: LOSE for cold positions, else WIN with lexicographically smallest move."""

LIM = 30


def _cold(a, b):
    for n in range(0, LIM):
        x = (n * (1 + 5 ** 0.5) / 2)
        xi = int(x + 1e-9)
        if xi >= LIM:
            break
        c, d = xi, xi + n
        if (a, b) == (c, d) or (a, b) == (d, c):
            return True
    return False


def solve(text: str) -> str:
    lines = text.split('\n')
    if not lines or lines[0].strip() == '':
        return ''
    a, b = map(int, lines[0].split()[:2])
    if _cold(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if ni >= 0 and nj >= 0 and (i == 0 or j == 0 or i == j) and _cold(ni, nj):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
