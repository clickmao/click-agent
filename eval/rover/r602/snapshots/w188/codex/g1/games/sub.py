def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))[:k]
    steps = [s for s in steps if s <= n]
    win = [False] * (n + 1)
    for total in range(1, n + 1):
        for s in steps:
            if s <= total and not win[total - s]:
                win[total] = True
                break
    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
