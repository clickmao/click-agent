"""多堆 Nim：WIN p r（堆号最小的必胜着法，每堆至多一个必胜着法）。"""


def solve(text: str) -> str:
    toks = text.split()
    m = int(toks[0])
    piles = [int(t) for t in toks[1:1 + m]]
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
