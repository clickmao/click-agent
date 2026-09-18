"""Nim: find the smallest-index pile with a valid winning reduction."""


def solve(text: str) -> str:
    nums = text.split()
    m = int(nums[0])
    piles = [int(x) for x in nums[1:1 + m]]

    total = 0
    for a in piles:
        total ^= a

    if total == 0:
        return "LOSE"

    for idx, a in enumerate(piles):
        target = a ^ total
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
