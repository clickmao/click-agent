"""Subtraction game (take-away), normal play convention.

stdin format:
    line 1: n k        (n stones, k allowed move sizes)
    line 2: s1 .. sk   (distinct sizes, contains 1)

Output: 'WIN m' with minimal winning first move, or 'LOSE'. No trailing newline.
"""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = sorted(int(t) for t in tokens[2:2 + k])

    # win[x] = True if the player to move with x stones can force a win.
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
