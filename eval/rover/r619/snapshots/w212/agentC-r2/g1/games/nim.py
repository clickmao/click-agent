"""Nim: minimal-index winning move."""


def solve(text: str) -> str:
    nums = [int(x) for x in text.split()]
    m = nums[0]
    piles = nums[1:1 + m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx, p in enumerate(piles):
        target = x ^ p
        if target < p:
            return 'WIN ' + str(idx + 1) + ' ' + str(p - target)
    return 'LOSE'
