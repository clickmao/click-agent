def solve(text):
    lines = text.strip().split("\n")
    n, k = map(int, lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())
    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for s in moves:
            if s <= t and not win[t - s]:
                win[t] = True
                break
    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
