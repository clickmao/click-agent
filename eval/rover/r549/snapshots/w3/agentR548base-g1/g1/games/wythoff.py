"""Wythoff's game: remove from one heap any amount, or equal positive amounts from both.

Stdin format: one line with two integers a b.
Output: 'LOSE' or 'WIN i j' with (i, j) lexicographically smallest winning move.
"""


def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    a, b = map(int, lines[0].split()[:2])

    # losing positions are (floor(n*phi), floor(n*phi^2))
    losing = set()
    for x in range(0, 27):
        y = int(x * 1.618033988749895) + 1
        if y > 60:
            break
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
            if (a - i, b - j) in losing:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
