"""多堆 Nim 必胜手。"""


def solve(text: str) -> str:
    vals = text.split()
    m = int(vals[0])
    piles = [int(x) for x in vals[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a

    if x == 0:
        return 'LOSE'

    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
