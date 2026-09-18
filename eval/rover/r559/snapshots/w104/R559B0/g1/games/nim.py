def solve(text):
    nums = text.split()
    m = int(nums[0])
    piles = [int(x) for x in nums[1:1 + m]]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(piles[i] - target)
    return 'LOSE'
