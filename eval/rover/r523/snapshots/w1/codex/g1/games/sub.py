def solve(text: str) -> str:
    data = text.split()
    n, k = int(data[0]), int(data[1])
    moves = sorted(int(x) for x in data[2:2 + k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in moves)
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
