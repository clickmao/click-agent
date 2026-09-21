def solve(text: str) -> str:
    nums = text.split()
    n = int(nums[0])
    k = int(nums[1])
    steps = [int(x) for x in nums[2:2 + k]]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
