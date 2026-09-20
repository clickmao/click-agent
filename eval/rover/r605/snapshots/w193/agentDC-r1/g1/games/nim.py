"""Multi-pile Nim: smallest-index pile with a winning move."""


def solve(text: str) -> str:
    toks = text.split()
    m = int(toks[0])
    piles = [int(x) for x in toks[1:1 + m]]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"
    for i, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
