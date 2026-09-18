"""Subtraction game: report a winning first move or LOSE."""


def solve(text):
    lines = text.splitlines()
    n = int(lines[0].split()[0])
    steps = [int(x) for x in lines[1].split()]
    steps.sort()
    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for s in steps:
            if s > t:
                break
            if not win[t - s]:
                win[t] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
