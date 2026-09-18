def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"
    for i in range(m):
        target = piles[i] ^ xor
        if target < piles[i]:
            return "WIN %d %d" % (i + 1, piles[i] - target)
    return "LOSE"
