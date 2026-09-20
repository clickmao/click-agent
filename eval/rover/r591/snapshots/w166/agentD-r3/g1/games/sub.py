def solve(text):
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    steps = list(map(int, lines[idx].split()))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
