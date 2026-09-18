def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    moves = [int(x) for x in lines[2:2 + k]]
    moves.sort()
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
            return 'WIN %d' % s
    return 'LOSE'
