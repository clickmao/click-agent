def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(t) for t in lines[0].split())
    steps = sorted(int(t) for t in lines[1].split())
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
