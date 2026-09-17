"""Wythoff's game: remove from one pile, or equal positive amounts from both.

solve(text) -> str : returns "LOSE" or "WIN i j" minimizing (i, j) lexicographically,
where i removed from pile 1 and j from pile 2 (i, j >= 0, not both zero).
"""


def solve(text: str) -> str:
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])

    # losing positions: (floor(t*phi), floor(t*phi^2)) sorted ascending by first coord
    phi = (1 + 5 ** 0.5) / 2
    losing = set()
    t = 0
    while True:
        x = int(t * phi)
        y = int(t * phi * phi)
        if x > 25 and y > 25:
            break
        if x <= 25 and y <= 25:
            losing.add((x, y))
            losing.add((y, x))
        t += 1

    if (a, b) in losing:
        return 'LOSE'

    best = None
    # rule (i): remove from pile 1 only -> (i, 0)
    for i in range(a + 1):
        if i == 0:
            continue
        if (a - i, b) in losing:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # rule (ii): remove from pile 2 only -> (0, j)
    for j in range(b + 1):
        if j == 0:
            continue
        if (a, b - j) in losing:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # rule (iii): remove equal amounts d from both -> (d, d)
    for d in range(1, min(a, b) + 1):
        if (a - d, b - d) in losing:
            cand = (d, d)
            if best is None or cand < best:
                best = cand

    return 'WIN %d %d' % best
