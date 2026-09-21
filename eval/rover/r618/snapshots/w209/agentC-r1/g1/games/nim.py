"""多堆 Nim: 堆号最小的必胜着法。"""


def solve(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return ""
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
