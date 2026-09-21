"""Nim: winning move (smallest pile index, then smallest number taken)."""


def solve(text: str) -> str:
    lines = text.split()
    pos = 0
    m = int(lines[pos]); pos += 1
    piles = [int(lines[pos + i]) for i in range(m)]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return "WIN %d %d" % (i + 1, piles[i] - target)
    return "LOSE"
