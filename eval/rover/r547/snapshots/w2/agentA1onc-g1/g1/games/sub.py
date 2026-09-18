"""Subtraction game: report a winning first move or LOSE.

Rules: two players alternately remove exactly one of the allowed numbers of
stones; the player taking the last stone wins.  The starting position is a
loss for the player to move iff it is a multiple of (min move + 1) -- but the
deduction is done by DP here so the general case stays correct.
"""


def solve(text: str) -> str:
    """Return ``WIN m`` (smallest winning first take) or ``LOSE``."""
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    moves = sorted({int(x) for x in data[2:2 + k]})

    # win[i] is True iff the player to move with i stones wins.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in moves)

    if not win[n]:
        return "LOSE"
    # Smallest move that leaves the opponent in a losing position.
    best = min(s for s in moves if s <= n and not win[n - s])
    return "WIN %d" % best
