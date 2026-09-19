def solve(text):
    tokens = text.split()
    pos = 0
    m = int(tokens[pos]); pos += 1
    piles = [int(tokens[pos + i]) for i in range(m)]

    total = 0
    for a in piles:
        total ^= a
    if total == 0:
        return "LOSE"
    for idx in range(m):
        target = piles[idx] ^ total
        if target < piles[idx]:
            return "WIN " + str(idx + 1) + " " + str(piles[idx] - target)
    return "LOSE"
