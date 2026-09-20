"""Multi-pile Nim: WIN with the smallest pile index having a winning move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    m = int(lines[idx].split()[0])
    piles = [int(x) for x in lines[idx + 1].split()[:m]]

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
