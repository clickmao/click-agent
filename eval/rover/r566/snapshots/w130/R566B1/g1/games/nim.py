"""Multi-pile Nim: smallest winning pile and the (unique) number to remove."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip()]
    m = int(lines[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    best = None
    for p, a in enumerate(piles):
        target = a ^ x
        if target < a:
            r = a - target
            if best is None or p < best[0]:
                best = (p, r)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % (best[0] + 1, best[1])
