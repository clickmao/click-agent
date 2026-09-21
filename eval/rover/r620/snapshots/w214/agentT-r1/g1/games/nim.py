def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(t) for t in tokens[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return "WIN " + str(i + 1) + " " + str(piles[i] - target)
    return "LOSE"
