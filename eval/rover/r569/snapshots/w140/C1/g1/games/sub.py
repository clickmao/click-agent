def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = sorted(set(int(x) for x in tokens[2:2 + k]))

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for mv in moves:
            if mv > i:
                break
            if not win[i - mv]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for mv in moves:
        if mv <= n and not win[n - mv]:
            return 'WIN %d' % mv
    return 'LOSE'
