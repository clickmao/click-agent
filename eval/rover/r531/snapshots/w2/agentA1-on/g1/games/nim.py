"""多堆 Nim: 每步从某一堆取走任意正数石子, 最后一颗者胜。"""


def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

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
