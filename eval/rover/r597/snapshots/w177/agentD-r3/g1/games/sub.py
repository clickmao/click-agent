def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    steps = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    choice = [None] * (n + 1)
    for i in range(1, n + 1):
        best = None
        for s in steps:
            if s <= i and not win[i - s]:
                best = s
                break
        if best is not None:
            win[i] = True
            choice[i] = best
    if win[n]:
        return 'WIN %d' % choice[n]
    return 'LOSE'
