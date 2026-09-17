"""Multi-pile Nim (normal play): report the smallest-index winning move."""


def solve(text: str) -> str:
    """Read m then m pile sizes.

    Return 'WIN p r' (smallest pile index p, take r stones from it) when the
    first player wins, else 'LOSE'. Each pile has at most one winning take.
    """
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"

    for i, a in enumerate(piles):
        # After taking r, pile i holds a-r and total xor must be 0.
        target = xor ^ a
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
