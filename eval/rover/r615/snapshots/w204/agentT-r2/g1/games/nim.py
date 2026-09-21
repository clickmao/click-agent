"""Nim: winning move on the smallest-index heap."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while len(piles) < m and idx < len(lines):
        piles.extend(int(x) for x in lines[idx].split())
        idx += 1
    piles = piles[:m]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"
    for i, a in enumerate(piles):
        take = a - (a ^ xor)
        if take > 0:
            return "WIN %d %d" % (i + 1, take)
    return "LOSE"
