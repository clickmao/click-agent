def solve(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in steps:
            if s <= m and not win[m - s]:
                win[m] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN ' + str(best)
