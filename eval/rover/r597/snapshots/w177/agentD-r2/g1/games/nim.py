def solve(text):
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(t) for t in tokens[1:1 + m]]

    xor = 0
    for a in piles:
        xor ^= a

    if xor == 0:
        return "LOSE"
    for p in range(m):
        target = piles[p] ^ xor
        if target < piles[p]:
            return "WIN " + str(p + 1) + " " + str(piles[p] - target)
    return "LOSE"
