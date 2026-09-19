def solve(text):
    tok = text.split()
    m = int(tok[0])
    piles = [int(x) for x in tok[1:1 + m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            take = piles[i] - target
            return "WIN " + str(i + 1) + " " + str(take)
    return "LOSE"
