"""Wythoff's game: remove from one pile, or equal amounts from both."""


def _isqrt(n: int) -> int:
    s = int(n ** 0.5)
    while (s + 1) * (s + 1) <= n:
        s += 1
    while s * s > n:
        s -= 1
    return s


def _cold(x: int, y: int) -> bool:
    """True iff the (unordered) position {x, y} is a P-position.

    Cold positions are the Wythoff pairs (floor(n*phi), floor(n*phi^2)).
    With d = |x - y| the pair is cold iff min(x, y) == floor(d * phi).
    """
    d = abs(x - y)
    # floor(d * phi) = (d + floor(d * sqrt(5))) // 2  (exact, integer-only)
    n = d
    floor_n_sqrt5 = _isqrt(5 * n * n)
    # floor(n*phi) = floor((n + floor(n*sqrt5)) / 2)
    floor_n_phi = (n + floor_n_sqrt5) // 2
    return min(x, y) == floor_n_phi and x >= 0 and y >= 0


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    candidates = []
    for t in range(1, min(a, b) + 1):      # equal amounts from both piles
        candidates.append((t, t))
    for i in range(1, a + 1):              # from first pile only
        candidates.append((i, 0))
    for j in range(1, b + 1):              # from second pile only
        candidates.append((0, j))

    for i, j in sorted(candidates):
        if _cold(a - i, b - j):
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
