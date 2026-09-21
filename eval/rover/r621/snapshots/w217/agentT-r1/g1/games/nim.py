"""多堆 Nim: WIN p r / LOSE。

输入首行: m
第二行: m 个堆大小 a1..am。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(v) for v in lines[1].split()][:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'

    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
