"""Subtraction game: must take exactly one of the allowed amounts; last stone wins.

Stdin format: first line 'n k', second line k distinct integers s1..sk (contains 1).
Output: 'WIN m' (smallest winning first move) or 'LOSE'.
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    n, k = map(int, lines[i].split())
    i += 1
    steps = []
    while i < len(lines) and len(steps) < k:
        steps.extend(int(x) for x in lines[i].split())
        i += 1
    steps = sorted(set(steps))

    # win[x] = True if the player to move with x stones can force a win
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s <= x and not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
