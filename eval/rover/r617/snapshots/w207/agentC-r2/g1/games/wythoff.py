"""Wythoff game solver."""


def _losing_pairs(limit=25):
    pairs = set()
    n = 0
    while True:
        a = int(n * (1 + 5 ** 0.5) / 2)
        b = a + n
        if a > limit and b > limit:
            break
        pairs.add((a, b))
        n += 1
    return pairs


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())

    limit = max(a, b)
    losing = _losing_pairs(limit)

    def is_losing(x, y):
        if x <= y:
            return (x, y) in losing
        return (y, x) in losing

    if is_losing(a, b):
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            if i > 0 and j == 0:
                ok = True
            if i == 0 and j > 0:
                ok = True
            if i > 0 and j > 0 and i == j:
                ok = True
            if not ok:
                continue
            if is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)

    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
