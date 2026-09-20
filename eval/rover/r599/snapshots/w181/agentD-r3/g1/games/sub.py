def solve(text):
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = sorted(int(x) for x in tokens[2:2 + k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for m in moves:
            if m <= i and not win[i - m]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for m in moves:
        if m <= n and not win[n - m]:
            return 'WIN ' + str(m)
    return 'LOSE'
