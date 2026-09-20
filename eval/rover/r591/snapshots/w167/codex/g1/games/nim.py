"""Multi-pile Nim: find the smallest-index winning move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]

    xor = 0
    for p in piles:
        xor ^= p
    if xor == 0:
        return "LOSE"

    for idx, p in enumerate(piles):
        target = p ^ xor
        if target < p:
            return "WIN %d %d" % (idx + 1, p - target)
    return "LOSE"
