def solve(text):
    lines = text.split("\n")
    n, k = (int(x) for x in lines[0].split())
    steps = sorted(set(int(x) for x in lines[1].split()))[:k]
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in steps:
            if s <= m and not win[m - s]:
                win[m] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
