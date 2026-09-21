def solve(text: str) -> str:
    toks = text.split()
    n = int(toks[0])
    k = int(toks[1])
    steps = [int(x) for x in toks[2:2 + k]]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if win[n]:
        for s in sorted(steps):
            if s <= n and not win[n - s]:
                return 'WIN %d' % s
    return 'LOSE'
