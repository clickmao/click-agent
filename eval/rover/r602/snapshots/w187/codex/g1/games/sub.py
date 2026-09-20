def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))[:k]
    win = [False] * (n + 1)
    for s in range(1, n + 1):
        win[s] = any(m <= s and not win[s - m] for m in moves)
    if not win[n]:
        return "LOSE"
    for m in moves:
        if m <= n and not win[n - m]:
            return "WIN %d" % m
