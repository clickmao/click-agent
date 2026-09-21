"""Multi-pile Nim: smallest-index winning move (pile, amount)."""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"
    for idx, a in enumerate(piles):
        target = xor ^ a
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
