"""多堆 Nim。"""


def solve(text: str) -> str:
    toks = text.split()
    p = 0
    m = int(toks[p]); p += 1
    piles = [int(toks[p + i]) for i in range(m)]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return 'WIN %d %d' % (i + 1, piles[i] - target)
    return 'LOSE'
