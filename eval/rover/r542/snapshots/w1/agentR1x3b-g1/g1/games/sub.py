def solve(text):
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    s = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for take in s:
            if take <= x and not win[x - take]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for take in s:
        if take <= n and not win[n - take]:
            best = take
            break
    return 'WIN %d' % best
