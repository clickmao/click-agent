"""Multi-pile Nim: winning move at smallest pile index."""


def solve(text):
    nums = text.split()
    m = int(nums[0])
    piles = [int(x) for x in nums[1:1 + m]]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return 'LOSE'
    for idx in range(m):
        a = piles[idx]
        target = a ^ xor
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
