def solve(text: str) -> str:
    nums = text.split()
    m = int(nums[0])
    a = [int(x) for x in nums[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = a[idx] ^ x
        if target < a[idx]:
            return 'WIN ' + str(idx + 1) + ' ' + str(a[idx] - target)
    return 'LOSE'
