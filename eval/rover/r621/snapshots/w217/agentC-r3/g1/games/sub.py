def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    tok = []
    for ln in lines:
        tok.extend(ln.split())
    it = iter(tok)
    n = int(next(it))
    k = int(next(it))
    steps = sorted({int(next(it)) for _ in range(k)})
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'WIN %d' % steps[0]
