"""Multi-pile Nim: smallest pile index winning move."""


def solve(text: str) -> str:
    lines = text.split()
    it = iter(lines)
    m = int(next(it))
    piles = [int(next(it)) for _ in range(m)]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for i, p in enumerate(piles):
        target = p ^ x
        if target < p:
            return "WIN %d %d" % (i + 1, p - target)
    return "LOSE"
