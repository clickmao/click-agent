def solve(text):
    lines = text.splitlines()
    if not lines:
        return 'LOSE'
    head = lines[0].split()
    if not head:
        return 'LOSE'
    n = int(head[0])
    if len(lines) > 1:
        steps = [int(x) for x in lines[1].split()]
    else:
        steps = [1]
    steps = sorted(set(s for s in steps if s >= 1))
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
            return 'WIN ' + str(s)
    return 'LOSE'
