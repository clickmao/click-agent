def solve(text):
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    steps = sorted(set(int(x) for x in lines[1].split()))

    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for s in steps:
            if s <= t and not win[t - s]:
                win[t] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
