def solve(text):
    parts = text.split()
    n = int(parts[0])
    k = int(parts[1])
    moves = list(map(int, parts[2:2 + k]))
    win = [False] * (n + 1)
    best = [None] * (n + 1)
    for i in range(1, n + 1):
        cands = []
        for s in moves:
            if s <= i and not win[i - s]:
                cands.append(s)
        if cands:
            win[i] = True
            best[i] = min(cands)
        else:
            win[i] = False
            best[i] = None
    if win[n]:
        return 'WIN %d' % best[n]
    return 'LOSE'
