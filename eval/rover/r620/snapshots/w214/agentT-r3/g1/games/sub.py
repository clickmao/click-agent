def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split()[:k])
    # win[i] = True 当且有 i 颗石子时是先手必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for s in steps:
            if s <= i and not win[i - s]:
                w = True
                break
        win[i] = w
    if not win[n]:
        return 'LOSE'
    best = None
    for s in steps:
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN %d' % best
