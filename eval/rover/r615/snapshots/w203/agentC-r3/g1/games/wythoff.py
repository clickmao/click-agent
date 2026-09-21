"""Wythoff's game: two players alternately either remove any positive
number of stones from one pile, or remove the same positive number from
both piles; the player taking the last stone wins.

solve(text) parses:
  line 1: a b  (pile sizes)
Returns 'LOSE' when the position is a cold (losing) position for the
player to move, else 'WIN i j' where taking i from the first pile and j
from the second pile is a winning move that is lexicographically
smallest in (i, j), with i, j >= 0 and not both zero. No trailing newline.
"""


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    def cold(x, y):
        # Wythoff cold positions: (floor(n*phi), floor(n*phi*phi)).
        if x == 0 and y == 0:
            return True
        lo, hi = (x, y) if x < y else (y, x)
        n = hi - lo
        if n <= 0:
            return False
        # floor(n * phi) == lo ?  using integer arithmetic
        return (lo * 2 - n) * (lo * 2 - n) == 5 * n * n + (2 * n * (lo * 2 - n) - 5 * n * n)

    def is_cold(x, y):
        if x == 0 and y == 0:
            return True
        lo, hi = (x, y) if x < y else (y, x)
        if hi == lo:
            return False
        n = hi - lo
        # lo must equal floor(n * (1 + sqrt(5)) / 2)
        return lo == (n * (1 + 5 ** 0.5)) // 2

    moves = []
    # option (i): remove from one pile only
    for i in range(a + 1):
        if i:
            moves.append((i, 0))
    for j in range(b + 1):
        if j:
            moves.append((0, j))
    # option (ii): remove the same positive number from both piles
    for t in range(1, min(a, b) + 1):
        moves.append((t, t))

    moves.sort()
    for i, j in moves:
        if is_cold(a - i, b - j):
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
