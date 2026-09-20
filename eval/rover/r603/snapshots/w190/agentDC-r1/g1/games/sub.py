def solve(text):
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))
    steps.sort()
    # win[i] = True if player to move with i stones wins
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in steps:
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN {}'.format(best)
