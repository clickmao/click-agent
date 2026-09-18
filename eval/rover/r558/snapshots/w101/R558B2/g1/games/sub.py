def solve(text: str) -> str:
    toks = text.split()
    n = int(toks[0])
    k = int(toks[1])
    steps = [int(toks[2 + i]) for i in range(k)]

    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for s in steps:
            if s <= stones and not win[stones - s]:
                win[stones] = True
                break

    if not win[n]:
        return 'LOSE'
    best = None
    for s in steps:
        if s <= n and not win[n - s]:
            if best is None or s < best:
                best = s
    return 'WIN ' + str(best)
