def solve(text):
    lines = text.split()
    it = iter(lines)
    n = int(next(it))
    k = int(next(it))
    steps = [int(next(it)) for _ in range(k)]
    win = [False] * (n + 1)
    move = [0] * (n + 1)
    for i in range(1, n + 1):
        best = None
        for s in steps:
            if s <= i and not win[i - s]:
                if best is None or s < best:
                    best = s
        if best is not None:
            win[i] = True
            move[i] = best
    if win[n]:
        return 'WIN ' + str(move[n])
    return 'LOSE'
