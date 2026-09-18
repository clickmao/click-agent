"""Multi-pile Nim: smallest-numbered pile with a winning move, and the amount."""


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    m = int(lines[0].split()[0])
    piles = [int(t) for t in lines[1].split()[:m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return "WIN %d %d" % (idx + 1, piles[idx] - target)
    return "LOSE"
