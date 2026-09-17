def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    moves = [int(x) for x in lines[1].split()][:k]
    moves = sorted(set(moves))
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in moves:
            if s <= m and not win[m - s]:
                win[m] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
