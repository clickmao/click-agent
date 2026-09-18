"""Wythoff's game: LOSE or WIN i j with lexicographically smallest (i, j)."""


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    return b - a == a


def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    a, b = (int(x) for x in lines[0].split())
    if _is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _is_losing(a - i, b - j):
                cand = (j, i)
                if best is None or cand < best:
                    best = cand
    return 'WIN ' + str(best[1]) + ' ' + str(best[0])
