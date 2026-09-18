def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    steps = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        win[m] = any(s <= m and not win[m - s] for s in steps)
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
