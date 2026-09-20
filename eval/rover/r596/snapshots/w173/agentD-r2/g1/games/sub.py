def solve(text):
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    moves = [int(x) for x in lines[1].split()[:k]]
    win = [False] * (n + 1)
    for s in range(1, n + 1):
        for mv in moves:
            if mv <= s and not win[s - mv]:
                win[s] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for mv in moves:
        if mv <= n and not win[n - mv]:
            if best is None or mv < best:
                best = mv
    return 'WIN %d' % best
