def solve(text: str) -> str:
    lines = text.strip("\n").split("\n")
    n, k = map(int, lines[0].split())
    moves = sorted(set(map(int, lines[1].split())))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(m <= i and not win[i - m] for m in moves)
    if not win[n]:
        return "LOSE"
    for m in moves:
        if m <= n and not win[n - m]:
            return "WIN %d" % m
    return "LOSE"
