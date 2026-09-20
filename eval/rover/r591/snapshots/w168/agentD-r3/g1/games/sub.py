def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())[:k]
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        win[m] = any(s <= m and not win[m - s] for s in moves)
    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN {0}".format(s)
    return "LOSE"
