"""Game ``sub``: subtract-a-square-set take-away game.

stdin:
    line 1:   n k        (1<=n<=80 stones ; 1<=k<=12 number of allowed moves)
    line 2:   k distinct integers s1..sk (1<=si<=12, includes 1)
stdout:
    'WIN m'  first player wins, m = numerically smallest winning first move
    'LOSE'   first player loses
    no trailing newline.

Play: two players alternate removing exactly one of the allowed amounts from a
single pile; whoever takes the last stone wins.
"""

from __future__ import annotations


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split()[:k])

    # win[i] = True if the player to move with i stones can force a win.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
