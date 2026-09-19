"""Subtraction game: WIN m (smallest winning first move) or LOSE."""


def solve(text):
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    steps = sorted(int(x) for x in lines[1].split())
    moving = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not moving[i - s]:
                moving[i] = True
                break
    if not moving[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not moving[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
