"""Nim: m piles, take any positive number from one pile; output WIN p r or LOSE."""


def solve(text: str) -> str:
    nums = [int(t) for t in text.split()]
    if not nums:
        return ''
    m = nums[0]
    piles = nums[1:1 + m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(len(piles)):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
