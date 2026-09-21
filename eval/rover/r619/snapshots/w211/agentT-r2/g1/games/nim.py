"""多堆 Nim：必胜手（堆号最小、该堆唯一必胜取数）。"""


def solve(text: str) -> str:
    nums = [int(x) for x in text.split()]
    m = nums[0]
    piles = nums[1:1 + m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
