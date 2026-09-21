def solve(text):
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = sorted(int(x) for x in tokens[2:2 + k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        res = False
        for s in moves:
            if s <= i and not win[i - s]:
                res = True
                break
        win[i] = res
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
