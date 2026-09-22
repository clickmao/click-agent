def solve(text: str) -> str:
    data = text.split()
    n, k = int(data[0]), int(data[1])
    steps = sorted(int(x) for x in data[2:2 + k])
    win = [False] * (n + 1)
    for total in range(1, n + 1):
        for s in steps:
            if s > total:
                break
            if not win[total - s]:
                win[total] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
