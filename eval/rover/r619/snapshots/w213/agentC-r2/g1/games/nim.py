"""Nim: first-player win with smallest heap index and amount taken."""


def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    piles = [int(x) for x in lines[idx].split()[:m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for i in range(len(piles)):
        a = piles[i]
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
