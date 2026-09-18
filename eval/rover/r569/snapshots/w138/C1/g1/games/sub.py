def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = [int(x) for x in tokens[2:2 + k]]

    win = [False] * (n + 1)
    best = [None] * (n + 1)
    for i in range(1, n + 1):
        cand = None
        winnable = False
        for s in steps:
            if s <= i and not win[i - s]:
                winnable = True
                if cand is None or s < cand:
                    cand = s
        win[i] = winnable
        best[i] = cand

    if win[n]:
        return 'WIN %d' % best[n]
    return 'LOSE'
