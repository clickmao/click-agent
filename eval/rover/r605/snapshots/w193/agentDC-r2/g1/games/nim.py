"""Multi-pile Nim: find the lexicographically smallest winning move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return "LOSE"
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m] if len(lines) > 1 else []
    while len(piles) < m:
        piles.append(0)

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    for idx in range(m):
        a = piles[idx]
        target = a ^ x
        if target < a:
            return "WIN " + str(idx + 1) + " " + str(a - target)
    return "LOSE"
