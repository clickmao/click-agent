def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    while lines[idx].strip() == '':
        idx += 1
    steps = list(map(int, lines[idx].split()))
    win = [False] * (n + 1)
    for cur in range(1, n + 1):
        ok = False
        for s in steps:
            if s <= cur and not win[cur - s]:
                ok = True
                break
        win[cur] = ok
    if not win[n]:
        return 'LOSE'
    for s in sorted(set(steps)):
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
