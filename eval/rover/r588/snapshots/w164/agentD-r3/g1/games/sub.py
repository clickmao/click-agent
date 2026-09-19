def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    steps = list(map(int, lines[idx + 1].split()))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        res = False
        for s in steps:
            if s <= i and not win[i - s]:
                res = True
                break
        win[i] = res
    if not win[n]:
        return 'LOSE'
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
