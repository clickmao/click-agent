"""Multi-pile Nim: WIN p r / LOSE.

stdin format:
    m
    a1..am
"""


def solve(text: str) -> str:
    nums = text.split()
    if not nums:
        return ''
    m = int(nums[0])
    piles = [int(x) for x in nums[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (i + 1, a - target)
    return 'LOSE'
