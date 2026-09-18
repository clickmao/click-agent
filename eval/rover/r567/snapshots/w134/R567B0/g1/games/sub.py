def solve(text):
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    steps = sorted(map(int, lines[1].split()))
    lose = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if lose[i - s]:
                continue
            lose[i] = True
            break
    if not lose[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and lose[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
