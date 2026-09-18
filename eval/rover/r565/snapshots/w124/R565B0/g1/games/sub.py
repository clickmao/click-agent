"""Subtraction game: first-player win/lose and smallest winning first move.

Input format:
    line 1: n k   (1<=n<=80 stones, 1<=k<=12)
    line 2: k distinct integers s1..sk (1<=si<=12, contains 1)

A move takes exactly one allowed amount; taking the last stone wins.
Output: `WIN m` where m is the numerically smallest winning first move,
        or `LOSE` if the first player loses.
"""


# 1 = winning position for the player to move, 0 = losing position.

def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    steps = [int(x) for x in lines[2:2 + k]]
    steps = sorted(set(steps))
    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for s in steps:
            if s > stones:
                break
            if not win[stones - s]:
                win[stones] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
