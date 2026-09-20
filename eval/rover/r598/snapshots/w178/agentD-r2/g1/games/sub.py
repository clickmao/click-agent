def solve(text: str) -> str:
    data = text.split()
    idx = 0
    n = int(data[idx]); idx += 1
    k = int(data[idx]); idx += 1
    steps = [int(data[idx + i]) for i in range(k)]
    steps = sorted(set(steps))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    smallest = None
    for s in steps:
        if s <= n and not win[n - s]:
            smallest = s
            break
    return "WIN " + str(smallest)
