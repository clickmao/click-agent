def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        win[x] = any(s <= x and not win[x - s] for s in moves)
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
