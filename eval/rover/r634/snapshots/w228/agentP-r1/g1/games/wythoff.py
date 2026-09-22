"""Wythoff game on <a> <b> (a is first pile, b is second pile):
output lexicographically smallest (i, j) winning move, or LOSE.
"""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    losing = set()
    for k in range(0, 30):
        x = int(k * (1 + 5 ** 0.5) / 2)
        y = x + k
        losing.add((x, y))
        losing.add((y, x))
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na == 0 and nb == 0:
                cand = (i, j)
            elif (na, nb) in losing:
                cand = (i, j)
            else:
                continue
            if best is None or cand < best:
                best = cand
    return 'WIN %d %d' % best
