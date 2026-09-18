def solve(text):
    lines = text.split('\n')
    p = 0
    while p < len(lines) and lines[p].strip() == '':
        p += 1
    n, k = map(int, lines[p].split())
    p += 1
    steps = []
    while len(steps) < k and p < len(lines):
        steps.extend(int(t) for t in lines[p].split())
        p += 1
    steps = sorted(set(steps))
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
