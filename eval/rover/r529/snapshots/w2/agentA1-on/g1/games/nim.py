"""Multi-pile Nim: last stone wins; report the smallest-pile winning move."""


def solve(text: str) -> str:
    """text = full stdin; return 'WIN p r' or 'LOSE'."""
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a

    if x == 0:
        return "LOSE"

    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
