"""Nim: find the winning first move (smallest heap, exact count)."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for idx, p in enumerate(piles, start=1):
        target = p ^ x
        if target < p:
            return "WIN " + str(idx) + " " + str(p - target)
    return "LOSE"
