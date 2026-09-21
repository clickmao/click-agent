def solve(text):
    data = text.split()
    if not data:
        return ""
    idx = 0
    n = int(data[idx]); idx += 1
    k = int(data[idx]); idx += 1
    steps = []
    for _ in range(k):
        steps.append(int(data[idx])); idx += 1
    steps = sorted(set(steps))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
