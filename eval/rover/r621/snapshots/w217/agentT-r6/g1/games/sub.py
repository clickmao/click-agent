def solve(text):
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = sorted(int(x) for x in tokens[2:2 + k])
    win = [False] * (n + 1)
    for cur in range(1, n + 1):
        for s in steps:
            if s > cur:
                break
            if not win[cur - s]:
                win[cur] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
