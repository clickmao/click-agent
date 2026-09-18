"""多堆 Nim: 给出堆号最小、取子数唯一的必胜着法。"""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'

    for idx, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return 'WIN %d %d' % (idx + 1, p - target)
    return 'LOSE'
