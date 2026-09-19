def solve(text):
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())
    win = [False] * (n + 1)
    for t in range(1, n + 1):
        win[t] = any(t - s >= 0 and not win[t - s] for s in moves)
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if n - s >= 0 and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
