def solve(text):
    toks = text.split()
    n = int(toks[0])
    k = int(toks[1])
    moves = [int(x) for x in toks[2:2 + k]]
    moves.sort()
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        ok = False
        for s in moves:
            if s <= x and not win[x - s]:
                ok = True
                break
        win[x] = ok
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
