"""Wythoff's game: detect cold (losing) positions and give the minimal move.

Moves: take any positive amount from one pile, or the same positive amount
from both piles. The player taking the last stone wins.

stdin: one line with two integers a b.
stdout: 'LOSE' if the position is a P-position, else 'WIN i j' where (i, j)
is the lexicographically smallest winning move (compare i first, then j).
Pure function: solve(text) -> str (no trailing newline).
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    a, b = (int(x) for x in lines[0].split()[:2])
    hi = max(a, b)

    # Precompute losing (cold) positions up to 'hi' via the Wythoff rule:
    # P-positions are (floor(phi*n), floor(phi*n)+n) with n = 0,1,2,...
    # d(n) = floor(n*phi)
    phi = (1 + 5 ** 0.5) / 2
    losing = set()
    n = 0
    while True:
        d = int(n * phi)
        x, y = d, d + n
        if x > hi and y > hi:
            break
        losing.add((x, y))
        losing.add((y, x))
        n += 1
        if n > 100:
            break

    if (a, b) in losing:
        return 'LOSE'

    # Try moves in lexicographic order of (i, j): i ascending, then j ascending.
    for i in range(0, a + 1):
        j_start = 0 if i > 0 else 1  # cannot take zero from both
        for j in range(j_start, b + 1):
            if not _valid_move(a, b, i, j):
                continue
            if (a - i, b - j) in losing:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'


def _valid_move(a: int, b: int, i: int, j: int) -> bool:
    # A legal move is: same positive amount from both, or positive from exactly one.
    if i > a or j > b:
        return False
    if i == j:
        return i > 0
    if i == 0:
        return j > 0
    if j == 0:
        return i > 0
    return False
