def solve(text):
    tok = text.split()
    n = int(tok[0])
    k = int(tok[1])
    steps = [int(x) for x in tok[2:2 + k]]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in steps:
        if s <= n and not win[n - s]:
            if best is None or s < best:
                best = s
    return 'WIN %d' % best
