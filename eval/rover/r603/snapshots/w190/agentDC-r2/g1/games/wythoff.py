"""Wythoff game: losing positions are (floor(n*phi), floor(n*phi*phi)).

For a losing position the answer is LOSE; otherwise the winning move
(i, j) must be lexicographically smallest with (i, j) != (0, 0).
We enumerate candidates by increasing i (then j) and test whether the
resulting position is a losing position of the Wythoff game.
"""

NMAX = 200


def _losers(limit):
    s = set()
    phi = (1 + 5 ** 0.5) / 2
    n = 0
    while True:
        a = int(n * phi)
        b = int(n * phi * phi)
        if a > limit and b > limit:
            break
        s.add((a, b))
        s.add((b, a))
        n += 1
    return s


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    losers = _losers(NMAX)
    if (a, b) in losers:
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in losers:
                return "WIN %d %d" % (i, j)
    return "LOSE"
