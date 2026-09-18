"""多堆 Nim：必胜着法（堆号最小，每堆至多一个必胜着法）。

solve(text): 首行 m；第二行 m 个整数 a1..am。
"""


def solve(text):
    toks = text.split()
    m = int(toks[0])
    piles = [int(t) for t in toks[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for p, a in enumerate(piles, start=1):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (p, a - target)
    return 'LOSE'
