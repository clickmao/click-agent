import sys


def solve(text: str) -> str:
    lines = text.split('\n')
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    n, k = map(int, lines[i].split())
    i += 1
    steps = sorted(map(int, lines[i].split()))
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in steps:
            if s <= m and not win[m - s]:
                win[m] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
