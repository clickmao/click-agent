def solve(text: str) -> str:
    lines = text.strip().split()
    idx = 0
    n = int(lines[idx]); idx += 1
    k = int(lines[idx]); idx += 1
    steps = [int(x) for x in lines[idx:idx + k]]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for s in steps:
            if s <= i and not win[i - s]:
                w = True
                break
        win[i] = w
    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
