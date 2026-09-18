def solve(text):
    lines = text.split('\n')
    first = lines[0].split()
    n, k = int(first[0]), int(first[1])
    moves = sorted(int(x) for x in lines[1].split()[:k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
