def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].strip())
    piles = list(map(int, lines[1].split()))
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return "WIN %d %d" % (i + 1, piles[i] - target)
    return "LOSE"
