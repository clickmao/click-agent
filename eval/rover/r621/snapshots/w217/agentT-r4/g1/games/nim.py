def solve(text):
    nums = text.split()
    m = int(nums[0])
    piles = [int(nums[1 + i]) for i in range(m)]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return 'WIN %d %d' % (i + 1, piles[i] - target)
    return 'LOSE'
