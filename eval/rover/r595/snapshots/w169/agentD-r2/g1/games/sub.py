def solve(text: str) -> str:
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    s = [int(x) for x in data[2:2 + k]]
    moves = sorted(s)
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for v in moves:
            if v > i:
                break
            if not win[i - v]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for v in moves:
        if v <= n and not win[n - v]:
            return 'WIN ' + str(v)
    return 'LOSE'
