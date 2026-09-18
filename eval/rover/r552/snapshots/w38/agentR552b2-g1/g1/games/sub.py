def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))
    win = [False] * (n + 1)
    move = [0] * (n + 1)
    for t in range(1, n + 1):
        for s in sorted(steps):
            if s <= t and not win[t - s]:
                win[t] = True
                move[t] = s
                break
    if win[n]:
        m = move[n]
        for s in sorted(steps):
            if s <= n and not win[n - s] and s < m:
                m = s
        return 'WIN %d' % m
    return 'LOSE'
