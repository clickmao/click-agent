def solve(text: str) -> str:
    tokens = text.split()
    pos = 0
    n = int(tokens[pos]); pos += 1
    k = int(tokens[pos]); pos += 1
    steps = [int(tokens[pos + i]) for i in range(k)]
    win = [False] * (n + 1)
    move = [None] * (n + 1)
    for x in range(1, n + 1):
        best = None
        for s in steps:
            if s <= x and not win[x - s]:
                if best is None or s < best:
                    best = s
        if best is not None:
            win[x] = True
            move[x] = best
    if win[n]:
        return 'WIN %d' % move[n]
    return 'LOSE'
