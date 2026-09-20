def solve(text):
    nums = text.split()
    it = iter(nums)
    n = int(next(it))
    k = int(next(it))
    steps = [int(next(it)) for _ in range(k)]
    steps = sorted(set(steps))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    best = None
    for s in steps:
        if s <= n and not win[n - s]:
            best = s
            break
    return "WIN %d" % best
