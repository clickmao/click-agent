def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    steps = sorted(map(int, lines[idx].split()))
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        res = False
        for s in steps:
            if s <= m and not win[m - s]:
                res = True
                break
        win[m] = res
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
