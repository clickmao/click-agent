def solve(text):
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    steps = sorted(set(map(int, lines[1].split()[:k])))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    smallest = None
    for s in steps:
        if s <= n and not win[n - s]:
            smallest = s
            break
    return 'WIN %d' % smallest
