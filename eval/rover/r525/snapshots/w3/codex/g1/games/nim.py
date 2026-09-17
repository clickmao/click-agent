"""Multi-pile Nim: report the smallest-index winning pile and stones to take."""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(t) for t in lines[1].split()][:m]

    xor = 0
    for v in piles:
        xor ^= v
    if xor == 0:
        return "LOSE"
    for idx, v in enumerate(piles):
        target = v ^ xor
        if target < v:
            return "WIN %d %d" % (idx + 1, v - target)
    return "LOSE"
