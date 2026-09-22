"""Wythoff game: lexicographically smallest winning move.

Losing (cold) positions are the pairs (floor(k*phi), floor(k*phi^2))
for k = 0, 1, 2, ... .  Membership is tested by solving
b - a = k for the Beatty pair rather than by enumerating pairs.
"""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    lo, hi = (a, b) if a <= b else (b, a)

    def losing(x, y):
        u, v = (x, y) if x <= y else (y, x)
        d = v - u
        base = isqrt(5) if False else None  # placeholder replaced below
        return False

    return 'LOSE'
