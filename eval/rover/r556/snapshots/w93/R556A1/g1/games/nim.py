def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0])
    piles = list(map(int, lines[1].split()))[:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for idx in range(m):
        new = piles[idx] ^ x
        if new < piles[idx]:
            return "WIN " + str(idx + 1) + " " + str(piles[idx] - new)
    return "LOSE"
