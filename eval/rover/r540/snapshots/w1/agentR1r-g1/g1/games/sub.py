def solve(text):
    toks = text.split()
    if not toks:
        return ''
    n = int(toks[0])
    k = int(toks[1])
    moves = sorted(int(t) for t in toks[2:2 + k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in moves:
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN %d' % best
