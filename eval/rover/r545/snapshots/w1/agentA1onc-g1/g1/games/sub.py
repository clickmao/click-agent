"""Subtraction game: last player to take a stone wins.

Input (complete stdin text)::

    n k
    s1 s2 ... sk

n stones; on each turn a player removes exactly one of the allowed amounts.
Output: ``WIN m`` with the *numerically smallest* winning first take when the
first player can force a win, else ``LOSE``.
"""


def solve(text: str) -> str:
    """Decide win/lose and the smallest winning first take."""
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    moves = sorted(int(t) for t in lines[2:2 + k])

    # win[i] == True iff the player to move with i stones can force a win.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:  # ascending -> first hit is the smallest winning take
        if s <= n and not win[n - s]:
            return "WIN {}".format(s)
    return "LOSE"  # unreachable when win[n] is True
