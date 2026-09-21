def solve(text):
    nums = text.split()
    pos = 0
    n = int(nums[pos]); pos += 1
    k = int(nums[pos]); pos += 1
    steps = [int(nums[pos + i]) for i in range(k)]
    steps = sorted(set(s for s in steps if s <= n))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
