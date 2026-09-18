"""Wythoff's game: remove from one pile, or the same positive amount from both.

Output the losing-position verdict, or the lexicographically smallest winning
move (i, j) meaning remove i from pile 1 and j from pile 2.

Losing (P-)positions are exactly the Beatty pairs ``(x, x + d)`` with
``d >= 0`` and ``x = floor(d * phi)``, ``phi = (1 + sqrt(5)) / 2``.
On sorted piles ``d = b - a`` is an exact integer, and ``x`` is computed by
comparing ``(2k - d) ** 2 <= 5 * d * d`` with integers only, so no floating
point comparison decides the answer.  The move scan walks legal moves in
lexicographic order, so the first winning move found is the smallest.
"""


def _isqrt(n: int) -> int:
    """Exact integer square root for n >= 0."""
    if n <= 0:
        return 0
    x = int(n ** 0.5)
    while x * x > n:
        x -= 1
    while (x + 1) * (x + 1) <= n:
        x += 1
    return x


def _floor_mul_phi(d: int) -> int:
    """floor(d * phi) computed exactly with integer arithmetic only.

    x = floor(d * phi)  <=>  x <= d * (1 + sqrt5) / 2 < x + 1
                        <=>  2x - d <= d * sqrt5 < 2x + 2 - d.
    Both sides are >= 0 for the candidate below (x >= d for d >= 0), so
    squaring preserves the inequality and only integers are involved.
    """
    x = (d + _isqrt(5 * d * d)) // 2  # safe starting point
    while x > 0 and (2 * x - d) * (2 * x - d) > 5 * d * d:
        x -= 1
    while (2 * (x + 1) - d) * (2 * (x + 1) - d) <= 5 * d * d:
        x += 1
    return x


def _is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    d = b - a
    return _floor_mul_phi(d) == a


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_losing(a, b):
        return "LOSE"

    # Legal moves in lexicographic order: (i, 0), (0, j), (t, t).
    cands = [(i, 0) for i in range(1, a + 1)]
    cands += [(0, j) for j in range(1, b + 1)]
    cands += [(t, t) for t in range(1, min(a, b) + 1)]
    cands.sort()

    for i, j in cands:
        if _is_losing(a - i, b - j):
            return "WIN %d %d" % (i, j)
    return "LOSE"
