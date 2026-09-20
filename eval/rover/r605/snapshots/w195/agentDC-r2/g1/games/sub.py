def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    steps = []
    while len(steps) < k and idx < len(lines):
        steps.extend(int(x) for x in lines[idx].split())
        idx += 1
    steps = sorted(steps)[:k]
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
            return "WIN %d" % s
    return "LOSE"
