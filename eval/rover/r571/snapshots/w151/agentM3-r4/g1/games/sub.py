def solve(text):
    nums = text.split()
    n = int(nums[0])
    k = int(nums[1])
    steps = sorted(int(nums[2 + i]) for i in range(k))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for s in steps:
            if s <= i and not win[i - s]:
                w = True
                break
        win[i] = w
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
