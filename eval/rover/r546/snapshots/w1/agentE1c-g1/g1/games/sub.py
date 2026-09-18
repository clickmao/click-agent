def solve(text: str) -> str:
    nums = text.split()
    n = int(nums[0])
    k = int(nums[1])
    moves = sorted(int(x) for x in nums[2:2 + k])
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for mv in moves:
            if mv > x:
                break
            if not win[x - mv]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    for mv in moves:
        if mv <= n and not win[n - mv]:
            return 'WIN ' + str(mv)
    return 'LOSE'
