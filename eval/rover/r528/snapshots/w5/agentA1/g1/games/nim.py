"""Multi-pile Nim: minimal-pile winning move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[0] == "":
        lines = lines[1:]
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

    xor = 0
    for p in piles:
        xor ^= p
    if xor == 0:
        return "LOSE"

    for idx, p in enumerate(piles):
        target = p ^ xor
        if target < p:  # each pile has at most one winning move
            return "WIN %d %d" % (idx + 1, p - target)
    return "LOSE"
