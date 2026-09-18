def solve(text):
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))[:k]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for s in steps:
            if s <= i and not win[i - s]:
                w = True
                break
        win[i] = w
    if not win[n]:
        return 'LOSE'
    best = None
    for s in steps:
        if s <= n and not win[n - s]:
            if best is None or s < best:
                best = s
    return 'WIN ' + str(best)
