def solve(text: str) -> str:
    ints = text.split()
    n = int(ints[0])
    k = int(ints[1])
    steps = sorted(int(x) for x in ints[2:2 + k])

    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in steps:
            if s > m:
                break
            if not win[m - s]:
                win[m] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
