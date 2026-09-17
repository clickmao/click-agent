def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in moves)

    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
