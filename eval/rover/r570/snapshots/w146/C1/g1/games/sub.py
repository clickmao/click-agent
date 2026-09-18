def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = sorted(int(x) for x in tokens[2:2 + k])
    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for s in moves:
            if s <= t and not win[t - s]:
                win[t] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
