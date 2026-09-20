"""Subtraction game: win/lose and minimal winning first move."""


def solve(text):
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    steps = sorted(map(int, lines[1].split()))
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
