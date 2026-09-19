def solve(text):
    lines = [ln for ln in text.split('\n')]
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    steps = []
    while len(steps) < k and idx < len(lines):
        for tok in lines[idx].split():
            steps.append(int(tok))
        idx += 1
    steps = steps[:k]
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        w = False
        for s in steps:
            if s <= x and not win[x - s]:
                w = True
                break
        win[x] = w
    if not win[n]:
        return 'LOSE'
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
