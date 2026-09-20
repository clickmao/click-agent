def solve(text: str) -> str:
    lines = text.strip().split()
    m = int(lines[0])
    piles = [int(x) for x in lines[1:1 + m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return "WIN %d %d" % (i + 1, piles[i] - target)
    return "LOSE"
