"""Subtraction game: report a winning move or LOSE.

Input format (complete stdin text)::

    n k
    s1 s2 ... sk

``n`` stones, each move removes exactly one of the allowed amounts ``si``
(the list always contains 1); the player taking the last stone wins.

Output: ``WIN m`` where ``m`` is the numerically smallest winning first
move, or ``LOSE`` if the first player is losing.
"""

from __future__ import annotations


def solve(text: str) -> str:
    """Return the first player's optimal outcome for the subtraction game."""
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    steps = sorted(int(x) for x in lines[2 : 2 + k])

    # win[i] == True  <=>  the player to move with i stones can force a win.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return f"WIN {s}"
    return "LOSE"  # unreachable: win[n] implies some legal move lands on LOSE
