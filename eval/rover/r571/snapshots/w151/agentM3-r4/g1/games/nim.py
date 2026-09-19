def solve(text):
    nums = text.split()
    m = int(nums[0])
    piles = [int(nums[1 + i]) for i in range(m)]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(piles[i] - target)
    return 'LOSE'
