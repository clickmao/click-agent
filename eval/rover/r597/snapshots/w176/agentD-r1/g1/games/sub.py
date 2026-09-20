def solve(text):
    tokens = text.split()
    if not tokens:
        return ''
    n = int(tokens[0])
    k = int(tokens[1])
    steps = [int(x) for x in tokens[2:2 + k]]
    steps.sort()
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
            return 'WIN %d' % s
    return 'LOSE'
