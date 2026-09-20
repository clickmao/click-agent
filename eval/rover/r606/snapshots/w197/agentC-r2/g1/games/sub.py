"""Subtraction game: determine win/lose and smallest winning first move."""


def solve(text):
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))[:k]
    steps = sorted(steps)
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
