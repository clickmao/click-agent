"""Wythoff game: cold (P-)position detection, lexicographically minimal winning move.

stdin format:
  line 1: a b  (1<=a<=25, 1<=b<=25)
Output: 'LOSE' if the position is a P-position, else 'WIN i j' with (i,j)
(removed from pile 1 and pile 2 respectively) the lexicographically smallest
winning move among all winning moves; i,j>=0, not both 0.
"""

# Cold positions of Wythoff's game within the given bound.
# Cold positions are (floor(phi*t), floor(phi^2*t)) and their swaps.
_PHI = (1.0 + 5.0 ** 0.5) / 2.0


def _cold_positions(limit: int):
    cold = set()
    t = 0
    while True:
        x = int(_PHI * t)
        y = int(_PHI * _PHI * t)
        if x > limit and y > limit:
            break
        cold.add((x, y))
        cold.add((y, x))
        t += 1
    return cold


def solve(text: str) -> str:
    nums = text.split()
    a = int(nums[0])
    b = int(nums[1])

    cold = _cold_positions(max(a, b))
    if (a, b) in cold:
        return 'LOSE'

    best = None
    # Move type (i): remove from exactly one pile.
    for i in range(1, a + 1):
        if (a - i, b) in cold:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(1, b + 1):
        if (a, b - j) in cold:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # Move type (ii): remove the same positive amount from both piles.
    for t in range(1, min(a, b) + 1):
        if (a - t, b - t) in cold:
            cand = (t, t)
            if best is None or cand < best:
                best = cand

    return 'WIN %d %d' % (best[0], best[1])
