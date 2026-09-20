def solve(text):
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        ok = False
        for s in steps:
            if s <= x and not win[x - s]:
                ok = True
                break
        win[x] = ok
    if not win[n]:
        return 'LOSE'
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
