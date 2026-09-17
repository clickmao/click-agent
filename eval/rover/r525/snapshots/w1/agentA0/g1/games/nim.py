"""多堆 Nim: 必胜手。"""


def solve(text: str) -> str:
    toks = text.split()
    m = int(toks[0])
    piles = [int(x) for x in toks[1:1 + m]]

    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"

    for i, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return "WIN %d %d" % (i + 1, p - target)
    return "LOSE"
