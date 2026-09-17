"""Subtraction game (take-away game): first-player win/lose + smallest winning move.

Input (complete stdin text):
    line 1: n k   (n stones; k allowed move sizes)
    line 2: k distinct integers s1..sk (each 1..12, guaranteed to contain 1)

Rules: two players alternate removing exactly one allowed number of stones;
whoever takes the last stone wins.

Output: 'WIN m' with m the smallest-numbered winning first move, or 'LOSE'.
"""

from typing import List


def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = (int(x) for x in lines[0].split())
    moves: List[int] = sorted(int(x) for x in lines[1].split())[:k]

    # win[i] == True iff the player to move with i stones can force a win.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:  # sorted ascending -> first hit is the smallest winning move
        if s <= n and not win[n - s]:
            return "WIN {}".format(s)
    return "LOSE"
