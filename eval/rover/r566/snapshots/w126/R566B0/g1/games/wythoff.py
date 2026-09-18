"""Wythoff game: LOSE or WIN i j with lexicographically smallest move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split()[:2])
    if a == b == 0:
        return 'LOSE'
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and (j == 0 or i == j):
                moves.append((i, j))
    moves.sort()
    for (i, j) in moves:
        na, nb = a - i, b - j
        ref = (na, nb) if na <= nb else (nb, na)
        if not is_losing(ref):
            return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'


def is_losing(pair):
    x, y = pair
    lo, hi = (x, y) if x <= y else (y, x)
    return lo == int((hi - lo) * 1.618033988749895 + 1e-9)
