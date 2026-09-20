"""多堆 Nim：先手必胜手（堆号最小、每堆至多一个必胜着法）。"""


def solve(text: str) -> str:
    nums = []
    for tok in text.split():
        nums.append(int(tok))
    m = nums[0]
    piles = nums[1:1 + m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        t = a ^ x
        if t < a:
            return 'WIN %d %d' % (i + 1, a - t)
    return 'LOSE'
