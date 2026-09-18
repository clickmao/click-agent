def _win(n, steps):
    w = [False] * (n + 1)
    for t in range(1, n + 1):
        for s in steps:
            if s <= t and not w[t - s]:
                w[t] = True
                break
    return w


def solve(text):
    nums = text.split()
    n = int(nums[0])
    k = int(nums[1])
    steps = sorted(int(x) for x in nums[2:2 + k])
    w = _win(n, steps)
    if not w[n]:
        return "LOSE"
    for s in steps:
        if n - s >= 0 and not w[n - s]:
            return "WIN %d" % s
    return "LOSE"
