def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"
    for p in range(m):
        target = piles[p] ^ xor
        if target < piles[p]:
            return "WIN %d %d" % (p + 1, piles[p] - target)
    return "LOSE"
